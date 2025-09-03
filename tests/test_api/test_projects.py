import pytest
from fastapi.testclient import TestClient

from app.database import Base, get_db
from main import app
from tests.test_db_config import TestingSessionLocal, engine


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


class TestProjectEndpoints:
    """Pruebas para los endpoints de proyectos"""

    def create_test_user_and_login(self):
        """Helper para crear un usuario de prueba y hacer login"""
        user_data = {
            "email": "testuser@example.com",
            "full_name": "Test User",
            "password": "Test123456",
            "phone_number": "+573001234567",
        }

        # Crear usuario
        register_response = client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201

        # Hacer login
        login_data = {"username": "testuser@example.com", "password": "Test123456"}
        login_response = client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        user_id = register_response.json()["id"]

        return headers, user_id

    def test_create_project_success(self):
        """Probar creación exitosa de proyecto"""
        headers, user_id = self.create_test_user_and_login()

        project_data = {
            "name": "Mi Proyecto de Investigación",
            "description": "Este es un proyecto de prueba",
            "research_type": "experimental",
            "institution": "Universidad Test",
            "research_group": "Grupo de Investigación Test",
            "category": "Tecnología",
            "status": "planning",
        }

        response = client.post("/api/v1/proyectos/", json=project_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == project_data["name"]
        assert data["description"] == project_data["description"]
        assert data["research_type"] == project_data["research_type"]
        assert data["institution"] == project_data["institution"]
        assert data["research_group"] == project_data["research_group"]
        assert data["category"] == project_data["category"]
        assert data["status"] == project_data["status"]
        assert data["owner_id"] == user_id
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_project_minimal_data(self):
        """Probar creación de proyecto con datos mínimos"""
        headers, user_id = self.create_test_user_and_login()

        project_data = {"name": "Proyecto Mínimo"}

        response = client.post("/api/v1/proyectos/", json=project_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == project_data["name"]
        assert data["description"] is None
        assert data["research_type"] is None
        assert data["institution"] is None
        assert data["research_group"] is None
        assert data["category"] is None
        assert data["status"] == "planning"  # Valor por defecto
        assert data["owner_id"] == user_id

    def test_create_project_without_authentication(self):
        """Probar creación de proyecto sin autenticación"""
        project_data = {"name": "Proyecto Sin Auth"}

        response = client.post("/api/v1/proyectos/", json=project_data)

        assert response.status_code == 401

    def test_create_project_invalid_token(self):
        """Probar creación de proyecto con token inválido"""
        project_data = {"name": "Proyecto Token Inválido"}
        headers = {"Authorization": "Bearer invalid_token"}

        response = client.post("/api/v1/proyectos/", json=project_data, headers=headers)

        assert response.status_code == 401

    def test_create_project_empty_name(self):
        """Probar creación de proyecto con nombre vacío"""
        headers, _ = self.create_test_user_and_login()

        project_data = {"name": ""}

        response = client.post("/api/v1/proyectos/", json=project_data, headers=headers)

        assert response.status_code == 422

    def test_create_project_whitespace_name(self):
        """Probar creación de proyecto con nombre solo espacios"""
        headers, _ = self.create_test_user_and_login()

        project_data = {"name": "   "}

        response = client.post("/api/v1/proyectos/", json=project_data, headers=headers)

        assert response.status_code == 422

    def test_create_project_missing_name(self):
        """Probar creación de proyecto sin nombre"""
        headers, _ = self.create_test_user_and_login()

        project_data = {"description": "Proyecto sin nombre"}

        response = client.post("/api/v1/proyectos/", json=project_data, headers=headers)

        assert response.status_code == 422

    def test_list_projects_empty(self):
        """Probar listado de proyectos cuando no hay ninguno"""
        headers, _ = self.create_test_user_and_login()

        response = client.get("/api/v1/proyectos/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_projects_with_data(self):
        """Probar listado de proyectos con datos"""
        headers, user_id = self.create_test_user_and_login()

        # Crear algunos proyectos
        projects_data = [
            {"name": "Proyecto 1", "description": "Descripción 1"},
            {"name": "Proyecto 2", "description": "Descripción 2"},
            {"name": "Proyecto 3", "status": "in_progress"},
        ]

        created_projects = []
        for project_data in projects_data:
            response = client.post(
                "/api/v1/proyectos/", json=project_data, headers=headers
            )
            assert response.status_code == 201
            created_projects.append(response.json())

        # Listar proyectos
        response = client.get("/api/v1/proyectos/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

        # Verificar que todos los proyectos pertenecen al usuario
        for project in data:
            assert project["id"] in [p["id"] for p in created_projects]
            assert "name" in project
            assert "status" in project
            assert "created_at" in project

    def test_list_projects_without_authentication(self):
        """Probar listado de proyectos sin autenticación"""
        response = client.get("/api/v1/proyectos/")

        assert response.status_code == 401

    def test_get_project_success(self):
        """Probar obtener proyecto específico exitosamente"""
        headers, _ = self.create_test_user_and_login()

        # Crear un proyecto
        project_data = {
            "name": "Proyecto de Prueba",
            "description": "Descripción de prueba",
            "research_type": "applied",
        }

        create_response = client.post(
            "/api/v1/proyectos/", json=project_data, headers=headers
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        # Obtener el proyecto
        response = client.get(f"/api/v1/proyectos/{project_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == project_data["name"]
        assert data["description"] == project_data["description"]
        assert data["research_type"] == project_data["research_type"]

    def test_get_project_not_found(self):
        """Probar obtener proyecto que no existe"""
        headers, _ = self.create_test_user_and_login()

        response = client.get("/api/v1/proyectos/999999", headers=headers)

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]

    def test_get_project_of_other_user(self):
        """Probar obtener proyecto de otro usuario"""
        # Crear primer usuario y proyecto
        headers1, _ = self.create_test_user_and_login()

        project_data = {"name": "Proyecto Usuario 1"}
        create_response = client.post(
            "/api/v1/proyectos/", json=project_data, headers=headers1
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        # Crear segundo usuario
        user_data_2 = {
            "email": "user2@example.com",
            "full_name": "User Two",
            "password": "Test123456",
            "phone_number": "+573001234568",
        }

        client.post("/api/v1/auth/register", json=user_data_2)
        login_data_2 = {"username": "user2@example.com", "password": "Test123456"}
        login_response_2 = client.post("/api/v1/auth/login", data=login_data_2)
        token_2 = login_response_2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token_2}"}

        # Intentar acceder al proyecto del primer usuario
        response = client.get(f"/api/v1/proyectos/{project_id}", headers=headers2)

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]

    def test_get_project_without_authentication(self):
        """Probar obtener proyecto sin autenticación"""
        response = client.get("/api/v1/proyectos/1")

        assert response.status_code == 401

    def test_update_project_success(self):
        """Probar actualización exitosa de proyecto"""
        headers, _ = self.create_test_user_and_login()

        # Crear un proyecto
        project_data = {
            "name": "Proyecto Original",
            "description": "Descripción original",
            "status": "planning",
        }

        create_response = client.post(
            "/api/v1/proyectos/", json=project_data, headers=headers
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        # Actualizar el proyecto
        update_data = {
            "name": "Proyecto Actualizado",
            "description": "Descripción actualizada",
            "status": "in_progress",
            "research_type": "experimental",
        }

        response = client.put(
            f"/api/v1/proyectos/{project_id}", json=update_data, headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
        assert data["status"] == update_data["status"]
        assert data["research_type"] == update_data["research_type"]

    def test_update_project_partial(self):
        """Probar actualización parcial de proyecto"""
        headers, _ = self.create_test_user_and_login()

        # Crear un proyecto
        project_data = {
            "name": "Proyecto Original",
            "description": "Descripción original",
            "research_type": "basic",
        }

        create_response = client.post(
            "/api/v1/proyectos/", json=project_data, headers=headers
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]
        original_data = create_response.json()

        # Actualizar solo el nombre
        update_data = {"name": "Solo Nombre Actualizado"}

        response = client.put(
            f"/api/v1/proyectos/{project_id}", json=update_data, headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == update_data["name"]
        # Verificar que otros campos no cambiaron
        assert data["description"] == original_data["description"]
        assert data["research_type"] == original_data["research_type"]

    def test_update_project_not_found(self):
        """Probar actualización de proyecto que no existe"""
        headers, _ = self.create_test_user_and_login()

        update_data = {"name": "Proyecto Inexistente"}

        response = client.put(
            "/api/v1/proyectos/999999", json=update_data, headers=headers
        )

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]

    def test_update_project_of_other_user(self):
        """Probar actualizar proyecto de otro usuario"""
        # Crear primer usuario y proyecto
        headers1, _ = self.create_test_user_and_login()

        project_data = {"name": "Proyecto Usuario 1"}
        create_response = client.post(
            "/api/v1/proyectos/", json=project_data, headers=headers1
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        # Crear segundo usuario
        user_data_2 = {
            "email": "user2@example.com",
            "full_name": "User Two",
            "password": "Test123456",
            "phone_number": "+573001234568",
        }

        client.post("/api/v1/auth/register", json=user_data_2)
        login_data_2 = {"username": "user2@example.com", "password": "Test123456"}
        login_response_2 = client.post("/api/v1/auth/login", data=login_data_2)
        token_2 = login_response_2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token_2}"}

        # Intentar actualizar el proyecto del primer usuario
        update_data = {"name": "Intento de Hackeo"}
        response = client.put(
            f"/api/v1/proyectos/{project_id}", json=update_data, headers=headers2
        )

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]

    def test_update_project_without_authentication(self):
        """Probar actualización de proyecto sin autenticación"""
        update_data = {"name": "Sin Auth"}

        response = client.put("/api/v1/proyectos/1", json=update_data)

        assert response.status_code == 401

    def test_delete_project_success(self):
        """Probar eliminación exitosa de proyecto"""
        headers, _ = self.create_test_user_and_login()

        # Crear un proyecto
        project_data = {"name": "Proyecto a Eliminar"}

        create_response = client.post(
            "/api/v1/proyectos/", json=project_data, headers=headers
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        # Eliminar el proyecto
        response = client.delete(f"/api/v1/proyectos/{project_id}", headers=headers)

        assert response.status_code == 204

        # Verificar que el proyecto ya no existe
        get_response = client.get(f"/api/v1/proyectos/{project_id}", headers=headers)
        assert get_response.status_code == 404

    def test_delete_project_not_found(self):
        """Probar eliminación de proyecto que no existe"""
        headers, _ = self.create_test_user_and_login()

        response = client.delete("/api/v1/proyectos/999999", headers=headers)

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]

    def test_delete_project_of_other_user(self):
        """Probar eliminar proyecto de otro usuario"""
        # Crear primer usuario y proyecto
        headers1, _ = self.create_test_user_and_login()

        project_data = {"name": "Proyecto Usuario 1"}
        create_response = client.post(
            "/api/v1/proyectos/", json=project_data, headers=headers1
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        # Crear segundo usuario
        user_data_2 = {
            "email": "user2@example.com",
            "full_name": "User Two",
            "password": "Test123456",
            "phone_number": "+573001234568",
        }

        client.post("/api/v1/auth/register", json=user_data_2)
        login_data_2 = {"username": "user2@example.com", "password": "Test123456"}
        login_response_2 = client.post("/api/v1/auth/login", data=login_data_2)
        token_2 = login_response_2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token_2}"}

        # Intentar eliminar el proyecto del primer usuario
        response = client.delete(f"/api/v1/proyectos/{project_id}", headers=headers2)

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]

        # Verificar que el proyecto sigue existiendo para el primer usuario
        get_response = client.get(f"/api/v1/proyectos/{project_id}", headers=headers1)
        assert get_response.status_code == 200

    def test_delete_project_without_authentication(self):
        """Probar eliminación de proyecto sin autenticación"""
        response = client.delete("/api/v1/proyectos/1")

        assert response.status_code == 401

    def test_project_validation_invalid_research_type(self):
        """Probar validación de tipo de investigación inválido"""
        headers, _ = self.create_test_user_and_login()

        project_data = {
            "name": "Proyecto con Tipo Inválido",
            "research_type": "invalid_type",
        }

        response = client.post("/api/v1/proyectos/", json=project_data, headers=headers)

        assert response.status_code == 422

    def test_project_validation_invalid_status(self):
        """Probar validación de estado inválido"""
        headers, _ = self.create_test_user_and_login()

        project_data = {
            "name": "Proyecto con Estado Inválido",
            "status": "invalid_status",
        }

        response = client.post("/api/v1/proyectos/", json=project_data, headers=headers)

        assert response.status_code == 422

    def test_project_name_length_validation(self):
        """Probar validación de longitud del nombre"""
        headers, _ = self.create_test_user_and_login()

        # Nombre muy largo (más de 255 caracteres)
        long_name = "A" * 256
        project_data = {"name": long_name}

        response = client.post("/api/v1/proyectos/", json=project_data, headers=headers)

        assert response.status_code == 422
