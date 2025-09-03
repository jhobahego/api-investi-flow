import pytest

from app.database import Base
from tests.test_db_config import client, engine


@pytest.fixture(autouse=True)
def setup_database():
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


class TestUserLogin:
    """Pruebas para los endpoints de login y logout"""

    def test_login_user_success(self) -> None:
        """Probar login exitoso de usuario"""
        # Crear un usuario primero
        user_data = {
            "email": "login@example.com",
            "full_name": "Login User",
            "password": "Test123456",
            "phone_number": "+573001234567",
        }

        register_response = client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201

        # Intentar login
        login_data = {"username": "login@example.com", "password": "Test123456"}

        response = client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 20  # JWT debería ser más largo

    def test_login_user_invalid_credentials(self) -> None:
        """Probar login con credenciales inválidas"""
        # Crear un usuario primero
        user_data = {
            "email": "login2@example.com",
            "full_name": "Login User 2",
            "password": "Test123456",
            "phone_number": "+573001234568",
        }

        register_response = client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201

        # Intentar login con contraseña incorrecta
        login_data = {"username": "login2@example.com", "password": "WrongPassword123"}

        response = client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_login_user_nonexistent(self) -> None:
        """Probar login con usuario que no existe"""
        login_data = {"username": "nonexistent@example.com", "password": "Test123456"}

        response = client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_login_missing_fields(self) -> None:
        """Probar login con campos faltantes"""
        # Sin username
        response1 = client.post("/api/v1/auth/login", data={"password": "Test123456"})
        assert response1.status_code == 422

        # Sin contraseña
        response2 = client.post(
            "/api/v1/auth/login", data={"username": "test@example.com"}
        )
        assert response2.status_code == 422

    def test_logout_user_success(self) -> None:
        """Probar logout exitoso con token válido"""
        # Crear un usuario y hacer login
        user_data = {
            "email": "logout@example.com",
            "full_name": "Logout User",
            "password": "Test123456",
            "phone_number": "+573001234569",
        }

        register_response = client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201

        login_data = {"username": "logout@example.com", "password": "Test123456"}

        login_response = client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Hacer logout
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/api/v1/auth/logout", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "logout@example.com" in data["message"]

    def test_logout_user_invalid_token(self) -> None:
        """Probar logout con token inválido"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.post("/api/v1/auth/logout", headers=headers)

        assert response.status_code == 401

    def test_logout_user_no_token(self) -> None:
        """Probar logout sin token"""
        response = client.post("/api/v1/auth/logout")

        assert (
            response.status_code == 401
        )  # FastAPI OAuth2PasswordBearer retorna 401 sin authorization header


class TestProtectedEndpoints:
    """Pruebas para endpoints protegidos que requieren autenticación"""

    def test_get_current_user_profile_success(self) -> None:
        """Probar acceso exitoso al perfil de usuario autenticado"""
        # Crear un usuario y hacer login
        user_data = {
            "email": "profile@example.com",
            "full_name": "Profile User",
            "password": "Test123456",
            "phone_number": "+573001234570",
            "university": "Universidad Test",
            "research_group": "Grupo Test",
            "career": "Carrera Test",
        }

        register_response = client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201

        login_data = {"username": "profile@example.com", "password": "Test123456"}

        login_response = client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Acceder al perfil con token válido
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/users/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert data["university"] == user_data["university"]
        assert data["research_group"] == user_data["research_group"]
        assert data["career"] == user_data["career"]
        # Verificar que la contraseña no se retorna
        assert "password" not in data
        assert "hashed_password" not in data

    def test_get_current_user_profile_no_token(self) -> None:
        """Probar acceso al perfil sin token"""
        response = client.get("/api/v1/users/me")

        assert (
            response.status_code == 401
        )  # FastAPI OAuth2PasswordBearer retorna 401 sin authorization header

    def test_get_current_user_profile_invalid_token(self) -> None:
        """Probar acceso al perfil con token inválido"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/users/me", headers=headers)

        assert response.status_code == 401
