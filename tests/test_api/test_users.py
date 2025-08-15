import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from main import app

# Configuración de testing (similar a test_auth.py)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestUserEndpoints:
    """Pruebas para los endpoints de usuarios"""

    def create_test_user(self):
        """Helper para crear un usuario de prueba"""
        user_data = {
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "Test123456",
            "phone_number": "+573001234567",
            "university": "Universidad Test",
            "research_group": "Grupo Test",
            "career": "Carrera Test",
        }
        response = client.post("/api/v1/auth/register", json=user_data)
        return response.json()

    def test_get_user_success(self):
        """Probar obtener usuario exitosamente"""
        created_user = self.create_test_user()
        user_id = created_user["id"]

        response = client.get(f"/api/v1/users/{user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["email"] == "test@example.com"
        assert data["phone_number"] == "+573001234567"

    def test_get_user_not_found(self):
        """Probar obtener usuario que no existe"""
        response = client.get("/api/v1/users/999999")

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]

    def test_update_user_success(self):
        """Probar actualizar usuario exitosamente"""
        created_user = self.create_test_user()
        user_id = created_user["id"]

        update_data = {
            "full_name": "Updated Name",
            "university": "Nueva Universidad",
            "career": "Nueva Carrera",
        }

        response = client.patch(f"/api/v1/users/{user_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["university"] == "Nueva Universidad"
        assert data["career"] == "Nueva Carrera"
        # Verificar que otros campos no cambiaron
        assert data["email"] == "test@example.com"
        assert data["research_group"] == "Grupo Test"

    def test_update_user_phone_number(self):
        """Probar actualizar número de teléfono"""
        created_user = self.create_test_user()
        user_id = created_user["id"]

        update_data = {"phone_number": "+573987654321"}

        response = client.patch(f"/api/v1/users/{user_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["phone_number"] == "+573987654321"

    def test_update_user_invalid_phone(self):
        """Probar actualizar con teléfono inválido"""
        created_user = self.create_test_user()
        user_id = created_user["id"]

        update_data = {"phone_number": "invalid_phone"}

        response = client.patch(f"/api/v1/users/{user_id}", json=update_data)

        assert response.status_code == 422

    def test_update_user_duplicate_phone(self):
        """Probar actualizar con teléfono duplicado"""
        # Crear primer usuario
        user_data_1 = {
            "email": "user1@example.com",
            "full_name": "User One",
            "password": "Test123456",
            "phone_number": "+573001234567",
        }
        client.post("/api/v1/auth/register", json=user_data_1)

        # Crear segundo usuario
        user_data_2 = {
            "email": "user2@example.com",
            "full_name": "User Two",
            "password": "Test123456",
            "phone_number": "+573001234568",
        }
        response2 = client.post("/api/v1/auth/register", json=user_data_2)
        user2_id = response2.json()["id"]

        # Intentar actualizar user2 con el teléfono de user1
        update_data = {"phone_number": "+573001234567"}

        response = client.patch(f"/api/v1/users/{user2_id}", json=update_data)

        assert response.status_code == 400
        assert "teléfono ya está registrado" in response.json()["detail"]

    def test_update_user_not_found(self):
        """Probar actualizar usuario que no existe"""
        update_data = {"full_name": "Updated Name"}

        response = client.patch("/api/v1/users/999999", json=update_data)

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]
