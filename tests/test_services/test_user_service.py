"""Tests para el servicio de usuarios"""

import pytest
from fastapi import HTTPException

from app.database import Base
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import user_service
from tests.test_db_config import TestingSessionLocal, engine


@pytest.fixture(autouse=True)
def setup_database():
    """Configurar base de datos para cada test"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Fixture para sesión de base de datos"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(db_session):
    """Fixture para crear un usuario de prueba"""
    user = User(
        email="testuser@example.com",
        full_name="Test User",
        hashed_password="hashed_password",
        phone_number="+573001234567",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestUserService:
    """Pruebas para el servicio de usuarios"""

    def test_create_user_success(self, db_session):
        """Probar creación exitosa de usuario"""
        user_data = UserCreate(
            email="newuser@example.com",
            full_name="New User",
            password="SecurePassword123",
            phone_number="+573009876543",
        )

        result = user_service.create_user(db=db_session, user_create=user_data)

        assert result is not None
        assert result.email == user_data.email
        assert result.full_name == user_data.full_name
        assert result.phone_number == user_data.phone_number
        assert result.is_active is True

    def test_create_user_duplicate_email(self, db_session, test_user):
        """Probar creación de usuario con email duplicado"""
        user_data = UserCreate(
            email=test_user.email,
            full_name="Duplicate User",
            password="SecurePassword123",
            phone_number="+573009876543",
        )

        with pytest.raises(HTTPException) as exc_info:
            user_service.create_user(db=db_session, user_create=user_data)

        assert exc_info.value.status_code == 400
        assert "email ya está registrado" in exc_info.value.detail

    def test_create_user_duplicate_phone(self, db_session, test_user):
        """Probar creación de usuario con teléfono duplicado"""
        user_data = UserCreate(
            email="newuser@example.com",
            full_name="Duplicate Phone User",
            password="SecurePassword123",
            phone_number=test_user.phone_number,
        )

        with pytest.raises(HTTPException) as exc_info:
            user_service.create_user(db=db_session, user_create=user_data)

        assert exc_info.value.status_code == 400
        assert "teléfono ya está registrado" in exc_info.value.detail

    def test_get_user_by_email_success(self, db_session, test_user):
        """Probar obtener usuario por email exitosamente"""
        result = user_service.get_user_by_email(db=db_session, email=test_user.email)

        assert result is not None
        assert result.id == test_user.id
        assert result.email == test_user.email

    def test_get_user_by_email_not_found(self, db_session):
        """Probar obtener usuario por email que no existe"""
        result = user_service.get_user_by_email(
            db=db_session, email="nonexistent@example.com"
        )

        assert result is None

    def test_get_user_by_id_success(self, db_session, test_user):
        """Probar obtener usuario por ID exitosamente"""
        result = user_service.get_user_by_id(db=db_session, user_id=test_user.id)

        assert result is not None
        assert result.id == test_user.id
        assert result.email == test_user.email

    def test_get_user_by_id_not_found(self, db_session):
        """Probar obtener usuario por ID que no existe"""
        result = user_service.get_user_by_id(db=db_session, user_id=99999)

        assert result is None

    def test_get_user_by_phone_success(self, db_session, test_user):
        """Probar obtener usuario por teléfono exitosamente"""
        result = user_service.get_user_by_phone(
            db=db_session, phone_number=test_user.phone_number
        )

        assert result is not None
        assert result.id == test_user.id
        assert result.phone_number == test_user.phone_number

    def test_get_user_by_phone_not_found(self, db_session):
        """Probar obtener usuario por teléfono que no existe"""
        result = user_service.get_user_by_phone(
            db=db_session, phone_number="+573009999999"
        )

        assert result is None

    def test_update_user_success(self, db_session, test_user):
        """Probar actualización exitosa de usuario"""
        update_data = UserUpdate(
            full_name="Updated Name",
            university="Universidad Actualizada",
            research_group="Grupo Actualizado",
        )

        result = user_service.update_user(
            db=db_session, user_id=test_user.id, user_update=update_data
        )

        assert result is not None
        assert result.id == test_user.id
        assert result.full_name == "Updated Name"
        assert result.university == "Universidad Actualizada"
        assert result.research_group == "Grupo Actualizado"

    def test_update_user_not_found(self, db_session):
        """Probar actualización de usuario que no existe"""
        update_data = UserUpdate(full_name="Updated Name")

        with pytest.raises(HTTPException) as exc_info:
            user_service.update_user(
                db=db_session, user_id=99999, user_update=update_data
            )

        assert exc_info.value.status_code == 404
        assert "Usuario no encontrado" in exc_info.value.detail

    def test_update_user_duplicate_phone(self, db_session):
        """Probar actualización con teléfono duplicado"""
        # Crear dos usuarios
        user1 = User(
            email="user1@example.com",
            full_name="User 1",
            hashed_password="hashed_password",
            phone_number="+573001111111",
            is_active=True,
        )
        user2 = User(
            email="user2@example.com",
            full_name="User 2",
            hashed_password="hashed_password",
            phone_number="+573002222222",
            is_active=True,
        )
        db_session.add_all([user1, user2])
        db_session.commit()
        db_session.refresh(user1)
        db_session.refresh(user2)

        # Intentar actualizar user1 con el teléfono de user2
        update_data = UserUpdate(phone_number=user2.phone_number)  # type: ignore[arg-type]

        with pytest.raises(HTTPException) as exc_info:
            user_service.update_user(
                db=db_session,
                user_id=user1.id,
                user_update=update_data,  # type: ignore[arg-type]
            )

        assert exc_info.value.status_code == 400
        assert "teléfono ya está registrado" in exc_info.value.detail

    def test_authenticate_user_success(self, db_session):
        """Probar autenticación exitosa de usuario"""
        # Crear usuario directamente con contraseña hasheada
        from app.core.security import get_password_hash

        password = "SecurePassword123"
        user = User(
            email="authuser@example.com",
            full_name="Auth User",
            hashed_password=get_password_hash(password),
            phone_number="+573003333333",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        result = user_service.authenticate_user(
            db=db_session,
            email=user.email,
            password=password,  # type: ignore[arg-type]
        )

        assert result is not None
        assert result.id == user.id  # type: ignore[comparison-overlap]
        assert result.email == user.email  # type: ignore[comparison-overlap]

    def test_authenticate_user_wrong_password(self, db_session):
        """Probar autenticación con contraseña incorrecta"""
        # Crear usuario
        from app.core.security import get_password_hash

        user = User(
            email="authuser@example.com",
            full_name="Auth User",
            hashed_password=get_password_hash("CorrectPassword123"),
            phone_number="+573003333333",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        result = user_service.authenticate_user(
            db=db_session,
            email=user.email,
            password="WrongPassword123",  # type: ignore[arg-type]
        )

        assert result is None

    def test_authenticate_user_not_found(self, db_session):
        """Probar autenticación con usuario que no existe"""
        result = user_service.authenticate_user(
            db=db_session, email="nonexistent@example.com", password="SomePassword123"
        )

        assert result is None

    def test_authenticate_user_by_identifier_success(self, db_session):
        """Probar autenticación por identificador (email) exitosamente"""
        # Crear usuario
        from app.core.security import get_password_hash

        password = "SecurePassword123"
        user = User(
            email="identuser@example.com",
            full_name="Ident User",
            hashed_password=get_password_hash(password),
            phone_number="+573004444444",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        result = user_service.authenticate_user_by_identifier(
            db=db_session,
            identifier=user.email,
            password=password,  # type: ignore[arg-type]
        )

        assert result is not None
        assert result.id == user.id  # type: ignore[comparison-overlap]
        assert result.email == user.email  # type: ignore[comparison-overlap]
