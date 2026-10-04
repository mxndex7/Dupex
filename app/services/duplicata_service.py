"""Regras de negócio das duplicatas.

Toda consulta é filtrada pelo dono: não há acesso cruzado entre usuários.
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import Duplicata, StatusDuplicata, User
from app.schemas import DuplicataCreate


def criar(db: Session, owner: User, data: DuplicataCreate) -> Duplicata:
    duplicata = Duplicata(
        numero=data.numero,
        valor_centavos=int(data.valor.scaleb(2)),
        emitente=data.emitente,
        sacado=data.sacado,
        data_emissao=date.today(),
        data_vencimento=data.data_vencimento,
        status=StatusDuplicata.EMITIDA,
        owner_id=owner.id,
    )
    db.add(duplicata)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Já existe uma duplicata com este número") from None
    return duplicata


def listar(
    db: Session, owner: User, status: StatusDuplicata | None, limit: int, offset: int
) -> tuple[list[Duplicata], int]:
    filters = [Duplicata.owner_id == owner.id]
    if status is not None:
        filters.append(Duplicata.status == status)

    total = db.scalar(select(func.count()).select_from(Duplicata).where(*filters)) or 0
    items = db.scalars(
        select(Duplicata).where(*filters).order_by(Duplicata.id.desc()).limit(limit).offset(offset)
    ).all()
    return list(items), total


def buscar(db: Session, owner: User, duplicata_id: int) -> Duplicata:
    duplicata = db.scalar(
        select(Duplicata).where(Duplicata.id == duplicata_id, Duplicata.owner_id == owner.id)
    )
    if duplicata is None:
        # Mesmo erro para "não existe" e "é de outro usuário": não revela a existência do recurso.
        raise NotFoundError("Duplicata não encontrada")
    return duplicata


def atualizar_status(
    db: Session, owner: User, duplicata_id: int, status: StatusDuplicata
) -> Duplicata:
    duplicata = buscar(db, owner, duplicata_id)
    duplicata.status = status
    db.commit()
    return duplicata


def excluir(db: Session, owner: User, duplicata_id: int) -> None:
    duplicata = buscar(db, owner, duplicata_id)
    db.delete(duplicata)
    db.commit()
