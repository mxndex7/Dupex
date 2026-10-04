from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.security import create_access_token
from app.schemas import Token, UserCreate, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Criar conta"
)
def register(data: UserCreate, db: DbSession):
    if not get_settings().allow_registration:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cadastro de novos usuários está desativado")
    return auth_service.register(db, data)


@router.post("/token", response_model=Token, summary="Obter token de acesso (login)")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    user = auth_service.authenticate(db, form.username, form.password)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut, summary="Usuário autenticado")
def me(user: CurrentUser):
    return user
