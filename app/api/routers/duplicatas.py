from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, DbSession
from app.models import StatusDuplicata
from app.schemas import DuplicataCreate, DuplicataOut, Page, StatusUpdate
from app.services import duplicata_service

router = APIRouter(prefix="/duplicatas", tags=["Duplicatas"])

NOT_FOUND = {404: {"description": "Duplicata não encontrada"}}


@router.post(
    "",
    response_model=DuplicataOut,
    status_code=status.HTTP_201_CREATED,
    summary="Emitir duplicata",
    responses={409: {"description": "Já existe duplicata com este número"}},
)
def criar_duplicata(data: DuplicataCreate, db: DbSession, user: CurrentUser):
    return duplicata_service.criar(db, user, data)


@router.get("", response_model=Page[DuplicataOut], summary="Listar duplicatas")
def listar_duplicatas(
    db: DbSession,
    user: CurrentUser,
    status: Annotated[StatusDuplicata | None, Query(description="Filtra por status.")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    items, total = duplicata_service.listar(db, user, status, limit, offset)
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{duplicata_id}", response_model=DuplicataOut, summary="Buscar duplicata", responses=NOT_FOUND
)
def buscar_duplicata(duplicata_id: int, db: DbSession, user: CurrentUser):
    return duplicata_service.buscar(db, user, duplicata_id)


@router.patch(
    "/{duplicata_id}/status",
    response_model=DuplicataOut,
    summary="Atualizar status",
    responses=NOT_FOUND,
)
def atualizar_status(duplicata_id: int, data: StatusUpdate, db: DbSession, user: CurrentUser):
    return duplicata_service.atualizar_status(db, user, duplicata_id, data.status)


@router.delete(
    "/{duplicata_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir duplicata",
    responses=NOT_FOUND,
)
def excluir_duplicata(duplicata_id: int, db: DbSession, user: CurrentUser):
    duplicata_service.excluir(db, user, duplicata_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
