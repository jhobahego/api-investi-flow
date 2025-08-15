from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
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
