from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserRepository:
    """Repositorio para operaciones CRUD de usuarios"""

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """Obtener un usuario por email"""
        return db.query(User).filter(User.email == email).first()  # type: ignore

    def get_by_id(self, db: Session, *, user_id: int) -> Optional[User]:
        """Obtener un usuario por ID"""
        return db.query(User).filter(User.id == user_id).first()  # type: ignore

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """Crear un nuevo usuario con contraseña hasheada"""
        hashed_password = get_password_hash(obj_in.password)
        db_obj = User(
            email=obj_in.email,
            full_name=obj_in.full_name,
            phone_number=obj_in.phone_number,
            university=obj_in.university,
            research_group=obj_in.research_group,
            career=obj_in.career,
            hashed_password=hashed_password,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: User, obj_in: UserUpdate) -> User:
        """Actualizar un usuario existente"""
        update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[User]:
        """Autenticar un usuario con email y contraseña"""
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):  # type: ignore
            return None
        return user

    def is_active(self, user: User) -> bool:
        """Verificar si un usuario está activo"""
        return bool(user.is_active)


# Instancia global del repositorio
user_repository = UserRepository()
