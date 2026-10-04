"""Configuração da aplicação, lida de variáveis de ambiente (prefixo ``DUPEX_``) e do ``.env``."""

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DUPEX_", env_file=".env", extra="ignore")

    app_name: str = "Dupex"
    version: str = "2.0.0"

    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'dupex.db'}"
    # Aplica as migrações do Alembic ao iniciar. Desligue se preferir rodar `alembic upgrade head`.
    auto_migrate: bool = True

    # Sem DUPEX_SECRET_KEY definida, uma chave aleatória é gerada a cada start:
    # funciona em desenvolvimento, mas invalida os tokens a cada reinício.
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(48), min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, gt=0)

    # Permite criar contas via POST /api/v1/auth/register.
    allow_registration: bool = True
    # Ex.: DUPEX_CORS_ORIGINS='["http://localhost:3000"]'. Vazio = CORS desligado.
    cors_origins: list[str] = []

    @property
    def secret_key_is_ephemeral(self) -> bool:
        return "secret_key" not in self.model_fields_set


@lru_cache
def get_settings() -> Settings:
    return Settings()
