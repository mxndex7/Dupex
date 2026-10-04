import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, utcnow
from app.models.user import User


class StatusDuplicata(enum.StrEnum):
    EMITIDA = "emitida"
    ACEITA = "aceita"
    LIQUIDADA = "liquidada"
    CANCELADA = "cancelada"


class Duplicata(Base):
    __tablename__ = "duplicatas"
    __table_args__ = (
        UniqueConstraint("owner_id", "numero", name="uq_duplicata_owner_numero"),
        Index("ix_duplicata_owner_status", "owner_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(30))
    # Valor em centavos (inteiro): evita erros de arredondamento de ponto flutuante.
    valor_centavos: Mapped[int]
    emitente: Mapped[str] = mapped_column(String(120))
    sacado: Mapped[str] = mapped_column(String(120))
    data_emissao: Mapped[date] = mapped_column(Date)
    data_vencimento: Mapped[date] = mapped_column(Date)
    status: Mapped[StatusDuplicata] = mapped_column(
        Enum(
            StatusDuplicata,
            native_enum=False,
            length=20,
            create_constraint=True,
            name="ck_duplicata_status",
            values_callable=lambda e: [member.value for member in e],
        ),
        default=StatusDuplicata.EMITIDA,
    )
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    owner: Mapped[User] = relationship(back_populates="duplicatas")

    @property
    def valor(self) -> Decimal:
        return (Decimal(self.valor_centavos) / 100).quantize(Decimal("0.01"))
