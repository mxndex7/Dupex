from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db, make_engine
from app.main import app

PASSWORD = "senha-segura-123"


@pytest.fixture()
def db_session_factory() -> Iterator[sessionmaker[Session]]:
    """Banco SQLite em memória, novo a cada teste."""
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture()
def client(db_session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Sem `with`: não dispara o lifespan (que rodaria as migrações no banco real).
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(client: TestClient, username: str) -> dict[str, str]:
    """Cria um usuário e devolve o cabeçalho Authorization pronto."""
    response = client.post(
        "/api/v1/auth/register", json={"username": username, "password": PASSWORD}
    )
    assert response.status_code == 201, response.text
    token = client.post(
        "/api/v1/auth/token", data={"username": username, "password": PASSWORD}
    ).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


@pytest.fixture()
def auth(client: TestClient) -> dict[str, str]:
    return make_user(client, "rafael")


@pytest.fixture()
def other_auth(client: TestClient) -> dict[str, str]:
    return make_user(client, "outra.pessoa")


def duplicata_payload(**overrides) -> dict:
    payload = {
        "numero": "DUP-001",
        "valor": "1500.00",
        "emitente": "Empresa XYZ Ltda",
        "sacado": "Cliente ABC S.A.",
        "data_vencimento": (date.today() + timedelta(days=30)).isoformat(),
    }
    payload.update(overrides)
    return payload
