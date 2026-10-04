import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routers import auth, duplicatas, health
from app.core.config import BASE_DIR, get_settings
from app.core.errors import DomainError

logger = logging.getLogger("dupex")

STATIC_DIR = BASE_DIR / "app" / "static"

DESCRIPTION = """
API RESTful para **duplicatas escriturais**: emissão, aceite e liquidação de títulos de crédito
em formato digital.

Faça login em `POST /api/v1/auth/token` (ou crie uma conta em `/auth/register`) e use o botão
**Authorize** para testar as rotas protegidas.
"""


def run_migrations() -> None:
    config = Config()
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    command.upgrade(config, "head")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.secret_key_is_ephemeral:
        logger.warning(
            "DUPEX_SECRET_KEY não definida: usando chave temporária (tokens expiram ao reiniciar)."
        )
    if settings.auto_migrate:
        run_migrations()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.app_name} — Duplicatas Escriturais",
        description=DESCRIPTION,
        version=settings.version,
        lifespan=lifespan,
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(duplicatas.router, prefix="/api/v1")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
