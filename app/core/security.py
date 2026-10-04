"""Hash de senhas (bcrypt) e tokens JWT."""

from datetime import timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.database import utcnow

# Hash descartável: gasta o mesmo tempo quando o usuário não existe (evita enumeração por timing).
_DUMMY_HASH = bcrypt.hashpw(b"dupex-dummy-password", bcrypt.gensalt()).decode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    """Confere a senha. Com ``password_hash=None`` (usuário inexistente), paga o mesmo custo."""
    try:
        matches = bcrypt.checkpw(password.encode(), (password_hash or _DUMMY_HASH).encode())
    except ValueError:
        return False
    return matches and password_hash is not None


def create_access_token(subject: int) -> str:
    settings = get_settings()
    now = utcnow()
    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub"]},
    )
