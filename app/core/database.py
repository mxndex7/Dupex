"""Engine, sessão e tipos base do SQLAlchemy."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import DateTime, create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator):
    """DateTime que sempre entra e sai como timezone-aware em UTC (SQLite não guarda fuso)."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)


def make_engine(url: str) -> Engine:
    parsed = make_url(url)
    kwargs: dict = {}

    if parsed.get_backend_name() == "sqlite":
        kwargs["connect_args"] = {"check_same_thread": False}
        if parsed.database in (None, "", ":memory:"):
            # Banco em memória precisa de uma única conexão compartilhada.
            kwargs["poolclass"] = StaticPool
        else:
            Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(url, **kwargs)

    if parsed.get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
