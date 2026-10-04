from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.config import get_settings

router = APIRouter(tags=["Sistema"])


@router.get("/health", summary="Health check")
def health(db: DbSession):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Banco de dados indisponível"
        ) from None
    settings = get_settings()
    return {"status": "ok", "servico": settings.app_name, "versao": settings.version}
