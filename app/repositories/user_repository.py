from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


class UserRepository:
    """Repositorio para operaciones CRUD de usuarios"""

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """Obtener un usuario por email"""
        return db.query(User).filter(User.email == email).first()  # type: ignore

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """Crear un nuevo usuario con contraseña hasheada"""
        hashed_password = get_password_hash(obj_in.password)
        db_obj = User(
            email=obj_in.email,
            full_name=obj_in.full_name,
            hashed_password=hashed_password,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[User]:
        """Autenticar un usuario con email y contraseña"""
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        """Verificar si un usuario está activo"""
        return bool(user.is_active)


# Instancia global del repositorio
user_repository = UserRepository()
