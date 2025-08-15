from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, get_current_user_email, security
from app.database import get_db
from app.schemas.token import LoginRequest, Token
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
def login_user(*, db: Session = Depends(get_db), login_data: LoginRequest) -> Token:
    """
    Iniciar sesión en el sistema.

    - **email**: Email del usuario registrado
    - **password**: Contraseña del usuario

    Retorna un token de acceso JWT válido por 30 minutos (por defecto).
    """
    # Autenticar al usuario
    user = user_service.authenticate_user(
        db, email=login_data.email, password=login_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not bool(user.is_active):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario inactivo"
        )

    # Crear token de acceso
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout")
def logout_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Cerrar sesión del usuario.

    Nota: Este endpoint invalida el token del lado del cliente.
    Para una invalidación completa del token, se requeriría una lista negra de tokens,
    lo cual está fuera del alcance de este prototipo.
    """
    # Verificar que el token sea válido
    current_user_email = get_current_user_email(credentials)

    return {
        "message": f"Sesión cerrada exitosamente para {current_user_email}",
        "detail": "Por favor, elimina el token del lado del cliente",
    }
