from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext

from app.core.config import BASE_DIR
from app.core.database import Base, make_engine


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_security_headers(client):
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_dashboard_e_swagger_disponiveis(client):
    assert "text/html" in client.get("/").headers["content-type"]
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_migracoes_geram_exatamente_o_schema_dos_modelos(tmp_path):
    """Se alguém alterar um modelo sem criar migração, este teste falha."""
    engine = make_engine(f"sqlite:///{tmp_path / 'migrado.db'}")
    config = Config()
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))

    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert diff == []
