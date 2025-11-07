"""Tests para los schemas de User"""

import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreate, UserResponse, UserUpdate


class TestUserSchemas:
    """Pruebas para los schemas de usuario"""

    def test_user_create_valid(self):
        """Probar creación de UserCreate con datos válidos"""
        user_data = {
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "SecurePassword123",
            "phone_number": "+573001234567",
        }

        user = UserCreate(**user_data)

        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.password == "SecurePassword123"
        assert user.phone_number == "+573001234567"

    def test_user_create_minimal_fields(self):
        """Probar creación de UserCreate con campos mínimos"""
        user_data = {
            "email": "minimal@example.com",
            "full_name": "Minimal User",
            "password": "SecurePass123",  # Debe cumplir requisitos
            "phone_number": "+573001234567",  # Requerido
        }

        user = UserCreate(**user_data)

        assert user.email == "minimal@example.com"
        assert user.full_name == "Minimal User"
        assert user.password == "SecurePass123"
        assert user.phone_number == "+573001234567"

    def test_user_create_invalid_email(self):
        """Probar validación de email inválido"""
        user_data = {
            "email": "invalid-email",
            "full_name": "Test User",
            "password": "Pass123",
        }

        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**user_data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("email",) for error in errors)

    def test_user_create_empty_email(self):
        """Probar validación con email vacío"""
        user_data = {"email": "", "full_name": "Test User", "password": "Pass123"}

        with pytest.raises(ValidationError):
            UserCreate(**user_data)

    def test_user_create_empty_full_name(self):
        """Probar validación con nombre vacío"""
        user_data = {
            "email": "test@example.com",
            "full_name": "",
            "password": "Pass123",
        }

        with pytest.raises(ValidationError):
            UserCreate(**user_data)

    def test_user_create_empty_password(self):
        """Probar validación con contraseña vacía"""
        user_data = {
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "",
        }

        with pytest.raises(ValidationError):
            UserCreate(**user_data)

    def test_user_update_partial_fields(self):
        """Probar actualización parcial de usuario"""
        update_data = {"full_name": "Updated Name"}

        user_update = UserUpdate(**update_data)

        assert user_update.full_name == "Updated Name"
        # UserUpdate no tiene campo email, solo campos de perfil
        assert user_update.phone_number is None

    def test_user_update_all_fields(self):
        """Probar actualización con todos los campos"""
        update_data = {
            "full_name": "Updated Name",
            "phone_number": "+573009876543",
            "university": "Universidad Actualizada",
            "research_group": "Grupo Actualizado",
            "career": "Carrera Actualizada",
        }

        user_update = UserUpdate(**update_data)

        assert user_update.full_name == "Updated Name"
        assert user_update.phone_number == "+573009876543"
        assert user_update.university == "Universidad Actualizada"

    def test_user_update_invalid_email(self):
        """Probar validación de teléfono inválido en actualización"""
        update_data = {"phone_number": "invalid-phone"}

        with pytest.raises(ValidationError) as exc_info:
            UserUpdate(**update_data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("phone_number",) for error in errors)

    def test_user_response_from_dict(self):
        """Probar creación de UserResponse desde diccionario"""
        from datetime import datetime

        user_data = {
            "id": 1,
            "email": "response@example.com",
            "full_name": "Response User",
            "phone_number": "+573001234567",
            "is_active": True,
            "is_verified": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        user_response = UserResponse(**user_data)

        assert user_response.id == 1
        assert user_response.email == "response@example.com"
        assert user_response.full_name == "Response User"
        assert user_response.is_active is True
        assert user_response.is_verified is False

    def test_user_response_excludes_password(self):
        """Probar que UserResponse no incluye la contraseña"""
        from datetime import datetime

        user_data = {
            "id": 1,
            "email": "test@example.com",
            "full_name": "Test User",
            "hashed_password": "should_not_appear",
            "is_active": True,
            "is_verified": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        user_response = UserResponse(**user_data)

        # Verificar que no tiene atributo password
        assert not hasattr(user_response, "password")
        assert not hasattr(user_response, "hashed_password")

    def test_user_response_optional_fields(self):
        """Probar UserResponse con campos opcionales"""
        from datetime import datetime

        user_data = {
            "id": 1,
            "email": "test@example.com",
            "full_name": "Test User",
            "phone_number": None,
            "university": None,
            "research_group": None,
            "career": None,
            "is_active": True,
            "is_verified": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        user_response = UserResponse(**user_data)

        assert user_response.phone_number is None
        assert user_response.university is None
        assert user_response.research_group is None
        assert user_response.career is None
