from datetime import timedelta

import jwt
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import utcnow
from tests.conftest import PASSWORD, make_user


def register(client: TestClient, username="rafael", password=PASSWORD):
    return client.post("/api/v1/auth/register", json={"username": username, "password": password})


def login(client: TestClient, username="rafael", password=PASSWORD):
    return client.post("/api/v1/auth/token", data={"username": username, "password": password})


def test_register_creates_user_without_exposing_hash(client):
    response = register(client)
    assert response.status_code == 201
    assert response.json() == {"id": 1, "username": "rafael"}


def test_register_is_case_insensitive_and_rejects_duplicates(client):
    register(client, "Rafael")
    response = register(client, "RAFAEL")
    assert response.status_code == 409


def test_register_validates_input(client):
    assert register(client, username="ab").status_code == 422
    assert register(client, username="com espaço").status_code == 422
    assert register(client, password="curta").status_code == 422
    assert register(client, password="é" * 40).status_code == 422  # 80 bytes > limite do bcrypt


def test_register_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "allow_registration", False)
    assert register(client).status_code == 403


def test_login_returns_bearer_token(client):
    register(client)
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_fails_with_wrong_password_or_unknown_user(client):
    register(client)
    wrong_password = login(client, password="senha-errada-123")
    unknown_user = login(client, username="ninguem")
    assert wrong_password.status_code == unknown_user.status_code == 401
    # Mesma mensagem nos dois casos: não revela quais usuários existem.
    assert wrong_password.json() == unknown_user.json()


def test_me_requires_valid_token(client, auth):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": "Bearer lixo"}).status_code == 401
    )
    response = client.get("/api/v1/auth/me", headers=auth)
    assert response.status_code == 200
    assert response.json()["username"] == "rafael"


def test_expired_token_is_rejected(client):
    make_user(client, "rafael")
    settings = get_settings()
    expired = jwt.encode(
        {"sub": "1", "exp": utcnow() - timedelta(minutes=1)},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_token_signed_with_another_key_is_rejected(client):
    make_user(client, "rafael")
    forged = jwt.encode(
        {"sub": "1", "exp": utcnow() + timedelta(hours=1)}, "x" * 32, algorithm="HS256"
    )
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_token_of_deleted_user_is_rejected(client, db_session_factory):
    headers = make_user(client, "rafael")
    from app.models import User

    with db_session_factory() as db:
        db.delete(db.get(User, 1))
        db.commit()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
