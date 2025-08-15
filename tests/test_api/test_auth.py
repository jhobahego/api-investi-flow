from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from main import app

# Base de datos en memoria para pruebas
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Generator[TestingSessionLocal, None, None]:  # type: ignore
    """Override de la dependencia de base de datos para pruebas"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    """Crear y limpiar la base de datos antes y después de cada prueba"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestUserRegistration:
    """Pruebas para el endpoint de registro de usuario"""

    def test_register_user_success(self) -> None:
        """Probar registro exitoso de usuario"""
        user_data = {
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "Test123456",
            "phone_number": "+573001234567",
            "university": "Universidad Nacional",
            "research_group": "Grupo de Investigación Test",
            "career": "Ingeniería de Sistemas",
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert data["phone_number"] == user_data["phone_number"]
        assert data["university"] == user_data["university"]
        assert data["research_group"] == user_data["research_group"]
        assert data["career"] == user_data["career"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["is_active"] is True
        assert data["is_verified"] is False
        # Verificar que la contraseña no se retorna
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_user_duplicate_email(self) -> None:
        """Probar registro con email duplicado"""
        user_data = {
            "email": "duplicate@example.com",
            "full_name": "Test User",
            "password": "Test123456",
            "phone_number": "+573001234567",
        }

        # Crear el primer usuario
        response1 = client.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code == 201

        # Intentar crear el segundo usuario con el mismo email
        user_data[
            "phone_number"
        ] = "+573001234568"  # Cambiar teléfono para evitar duplicado
        response2 = client.post("/api/v1/auth/register", json=user_data)
        assert response2.status_code == 400
        assert "email ya está registrado" in response2.json()["detail"]

    def test_register_user_minimal_data(self) -> None:
        """Probar registro con datos mínimos requeridos"""
        user_data = {
            "email": "minimal@example.com",
            "full_name": "Minimal User",
            "password": "Test123456",
            "phone_number": "+573001234567",
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["university"] is None
        assert data["research_group"] is None
        assert data["career"] is None

    def test_register_user_invalid_phone(self) -> None:
        """Probar registro con teléfono inválido"""
        invalid_phones = [
            "123456789",  # Sin código de país
            "+1234567890",  # Código de país incorrecto
            "+57123",  # Muy corto
            "+57312345678901234",  # Muy largo
            "+570123456789",  # Código de área inválido
        ]

        for i, phone in enumerate(invalid_phones):
            user_data = {
                "email": f"test{i}@example.com",
                "full_name": "Test User",
                "password": "Test123456",
                "phone_number": phone,
            }

            response = client.post("/api/v1/auth/register", json=user_data)
            assert response.status_code == 422

    def test_register_user_duplicate_phone(self) -> None:
        """Probar registro con teléfono duplicado"""
        user_data_1 = {
            "email": "user1@example.com",
            "full_name": "User One",
            "password": "Test123456",
            "phone_number": "+573001234567",
        }

        user_data_2 = {
            "email": "user2@example.com",
            "full_name": "User Two",
            "password": "Test123456",
            "phone_number": "+573001234567",  # Mismo teléfono
        }

        # Crear el primer usuario
        response1 = client.post("/api/v1/auth/register", json=user_data_1)
        assert response1.status_code == 201

        # Intentar crear el segundo usuario con el mismo teléfono
        response2 = client.post("/api/v1/auth/register", json=user_data_2)
        assert response2.status_code == 400
        assert "teléfono ya está registrado" in response2.json()["detail"]

    def test_register_user_missing_phone(self) -> None:
        """Probar registro sin teléfono (debe fallar)"""
        user_data = {
            "email": "nophone@example.com",
            "full_name": "No Phone User",
            "password": "Test123456",
        }

        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 422

    def test_register_user_invalid_email(self) -> None:
        """Probar registro con email inválido"""
        user_data = {
            "email": "invalid-email",
            "full_name": "Test User",
            "password": "Test123456",
        }

        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 422

    def test_register_user_weak_password(self) -> None:
        """Probar registro con contraseña débil"""
        test_cases = [
            {
                "email": "test1@example.com",
                "full_name": "Test User",
                "password": "123",  # Muy corta
                "phone_number": "+573001234567",
            },
            {
                "email": "test2@example.com",
                "full_name": "Test User",
                "password": "nouppercasenumber",  # Sin mayúscula ni número
                "phone_number": "+573001234568",
            },
            {
                "email": "test3@example.com",
                "full_name": "Test User",
                "password": "NOLOWERCASE123",  # Sin minúscula
                "phone_number": "+573001234569",
            },
            {
                "email": "test4@example.com",
                "full_name": "Test User",
                "password": "NoNumbers",  # Sin números
                "phone_number": "+573001234570",
            },
        ]

        for user_data in test_cases:
            response = client.post("/api/v1/auth/register", json=user_data)
            assert response.status_code == 422

    def test_register_user_empty_full_name(self) -> None:
        """Probar registro con nombre vacío"""
        user_data = {
            "email": "test@example.com",
            "full_name": " ",  # Nombre vacío
            "password": "Test123456",
            "phone_number": "+573001234567",
        }

        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 422

    def test_register_user_missing_fields(self) -> None:
        """Probar registro con campos faltantes"""
        # Sin email
        response1 = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Test User",
                "password": "Test123456",
                "phone_number": "+573001234567",
            },
        )
        assert response1.status_code == 422

        # Sin nombre
        response2 = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "Test123456",
                "phone_number": "+573001234567",
            },
        )
        assert response2.status_code == 422

        # Sin contraseña
        response3 = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "full_name": "Test User",
                "phone_number": "+573001234567",
            },
        )
        assert response3.status_code == 422
