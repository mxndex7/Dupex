from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.duplicata import StatusDuplicata

T = TypeVar("T")

Texto = Annotated[str, Field(min_length=2, max_length=120)]


class DuplicataCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "numero": "DUP-001",
                "valor": "1500.00",
                "emitente": "Empresa XYZ Ltda",
                "sacado": "Cliente ABC S.A.",
                "data_vencimento": "2030-12-31",
            }
        },
    )

    numero: Annotated[
        str, Field(min_length=1, max_length=30, description="Número único por usuário.")
    ]
    valor: Annotated[
        Decimal,
        Field(
            gt=0,
            max_digits=14,
            decimal_places=2,
            description="Valor em reais, com até 2 casas decimais.",
        ),
    ]
    emitente: Texto
    sacado: Texto
    data_vencimento: Annotated[date, Field(description="Não pode estar no passado.")]

    @field_validator("data_vencimento")
    @classmethod
    def vencimento_nao_pode_estar_no_passado(cls, value: date) -> date:
        if value < date.today():
            raise ValueError("data_vencimento não pode estar no passado")
        return value


class StatusUpdate(BaseModel):
    status: StatusDuplicata


class DuplicataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    valor: Decimal
    emitente: str
    sacado: str
    data_emissao: date
    data_vencimento: date
    status: StatusDuplicata
    created_at: datetime
    updated_at: datetime


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(description="Total de registros que atendem ao filtro.")
    limit: int
    offset: int
