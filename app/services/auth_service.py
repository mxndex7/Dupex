from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas import UserCreate


def get_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username.lower()))


def register(db: Session, data: UserCreate) -> User:
    user = User(username=data.username, password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Nome de usuário já está em uso") from None
    return user


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = get_by_username(db, username)
    if verify_password(password, user.password_hash if user else None):
        return user
    return None
