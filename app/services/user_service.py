from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import user_repository
from app.schemas.user import UserCreate, UserResponse, UserUpdate


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

        # Verificar si el número de teléfono ya está registrado (solo si se proporciona)
        if user_create.phone_number:
            existing_phone = self.get_user_by_phone(
                db, phone_number=user_create.phone_number
            )
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El número de teléfono ya está registrado en el sistema",
                )

        # Crear el usuario
        user = user_repository.create(db, obj_in=user_create)
        return UserResponse.model_validate(user)  # type: ignore

    def get_user_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """Obtener un usuario por email"""
        return user_repository.get_by_email(db, email=email)

    def get_user_by_id(self, db: Session, *, user_id: int) -> Optional[User]:
        """Obtener un usuario por ID"""
        return user_repository.get_by_id(db, user_id=user_id)

    def get_user_by_phone(self, db: Session, *, phone_number: str) -> Optional[User]:
        """Obtener un usuario por número de teléfono"""
        from sqlalchemy import func

        return (
            db.query(User)
            .filter(
                User.phone_number.isnot(None),  # Excluir usuarios con phone_number nulo
                func.lower(User.phone_number) == func.lower(phone_number),
            )
            .first()
        )  # type: ignore

    def update_user(
        self, db: Session, *, user_id: int, user_update: UserUpdate
    ) -> UserResponse:
        """Actualizar un usuario existente"""
        user = self.get_user_by_id(db, user_id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        # Si se está actualizando el teléfono, verificar que no esté en uso
        if user_update.phone_number and user_update.phone_number != user.phone_number:  # type: ignore
            existing_phone = self.get_user_by_phone(
                db, phone_number=user_update.phone_number
            )
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El número de teléfono ya está registrado en el sistema",
                )

        updated_user = user_repository.update(db, db_obj=user, obj_in=user_update)
        return UserResponse.model_validate(updated_user)  # type: ignore

    def authenticate_user(
        self, db: Session, *, email: str, password: str
    ) -> Optional[User]:
        """Autenticar un usuario"""
        return user_repository.authenticate(db, email=email, password=password)


# Instancia global del servicio
user_service = UserService()
