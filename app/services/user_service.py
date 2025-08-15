from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import user_repository
from app.schemas.user import UserCreate, UserResponse


class UserService:
    """Servicio para lógica de negocio de usuarios"""

    def create_user(self, db: Session, *, user_create: UserCreate) -> UserResponse:
        """Crear un nuevo usuario"""
        # Verificar si el email ya está registrado
        existing_user = user_repository.get_by_email(db, email=user_create.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado en el sistema",
            )

        # Crear el usuario
        user = user_repository.create(db, obj_in=user_create)
        return UserResponse.model_validate(user)  # type: ignore

    def get_user_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """Obtener un usuario por email"""
        return user_repository.get_by_email(db, email=email)

    def authenticate_user(
        self, db: Session, *, email: str, password: str
    ) -> Optional[User]:
        """Autenticar un usuario"""
        return user_repository.authenticate(db, email=email, password=password)


# Instancia global del servicio
user_service = UserService()
