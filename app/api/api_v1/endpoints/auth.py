from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    oauth2_scheme,
    verify_token,
)
from app.database import get_db
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import user_service

router = APIRouter()


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register_user(
    *, db: Session = Depends(get_db), user_in: UserCreate
) -> UserResponse:
    """
    Registrar un nuevo usuario en el sistema.

    - **email**: Email válido del usuario (único en el sistema)
    - **full_name**: Nombre completo del usuario
    - **password**: Contraseña segura (mínimo 8 caracteres, una mayúscula, una minúscula, un número)
    - **phone_number**: Número de teléfono colombiano (ej: +573001234567 para móvil, +5714567890 para fijo)
    - **university**: Nombre de la universidad (opcional)
    - **research_group**: Semillero de investigación (opcional)
    - **career**: Carrera universitaria (opcional)
    """
    try:
        user = user_service.create_user(db=db, user_create=user_in)
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}",
        )


@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = user_service.authenticate_user_by_identifier(
        db, identifier=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    elif not bool(user.is_active):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    return {
        "access_token": create_access_token(
            user.email, expires_delta=access_token_expires
        ),
        "refresh_token": create_refresh_token(user.email),
        "token_type": "bearer",
    }


@router.post("/logout")
def logout_user(token: str = Depends(oauth2_scheme)):
    """
    Cerrar sesión del usuario.

    Nota: Este endpoint invalida el token del lado del cliente.
    Para una invalidación completa del token, se requeriría una lista negra de tokens,
    lo cual está fuera del alcance de este prototipo.
    """
    # Verificar que el token sea válido
    email = verify_token(token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudieron validar las credenciales",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "message": f"Sesión cerrada exitosamente para {email}",
        "detail": "Por favor, elimina el token del lado del cliente",
    }
