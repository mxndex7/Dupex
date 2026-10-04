from alembic import context

from app.core.config import get_settings
from app.core.database import Base, make_engine
from app.models import Duplicata, User  # noqa: F401  (registra as tabelas no metadata)

config = context.config
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Permite que quem chama (testes, app) injete uma conexão própria.
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return

    engine = make_engine(get_settings().database_url)
    with engine.connect() as connection:
        _run(connection)
    engine.dispose()


def _run(connection) -> None:
    # render_as_batch: o SQLite não tem ALTER TABLE completo; o batch recria a tabela se preciso.
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
