import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

USERNAME_RE = re.compile(r"^[a-z0-9_.-]+$")


class UserCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: Annotated[
        str, Field(min_length=3, max_length=32, description="Letras, números, `_`, `.` e `-`.")
    ]
    password: Annotated[str, Field(min_length=8, max_length=72)]

    @field_validator("username")
    @classmethod
    def normalizar_username(cls, value: str) -> str:
        value = value.lower()
        if not USERNAME_RE.match(value):
            raise ValueError("username aceita apenas letras, números, '_', '.' e '-'")
        return value

    @field_validator("password")
    @classmethod
    def limite_bcrypt(cls, value: str) -> str:
        # bcrypt só considera os 72 primeiros bytes; recusamos em vez de truncar em silêncio.
        if len(value.encode()) > 72:
            raise ValueError("password deve ter no máximo 72 bytes")
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
