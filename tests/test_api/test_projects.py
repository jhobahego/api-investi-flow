import pytest

from app.database import Base
from tests.test_db_config import client, engine


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
        """Probar archivado (soft-delete) exitoso de proyecto"""
        headers, _ = self.create_test_user_and_login()

        # Crear un proyecto
        project_data = {"name": "Proyecto a Eliminar"}

        create_response = client.post(
            "/api/v1/proyectos/", json=project_data, headers=headers
        )
        assert create_response.status_code == 201
        assert create_response.json()["deleted_at"] is None
        project_id = create_response.json()["id"]

        # Archivar el proyecto (soft-delete)
        response = client.delete(f"/api/v1/proyectos/{project_id}", headers=headers)

        assert response.status_code == 204

        # Verificar que el proyecto ya no es accesible por id (404)
        get_response = client.get(f"/api/v1/proyectos/{project_id}", headers=headers)
        assert get_response.status_code == 404

        # Verificar que queda excluido del listado general
        list_response = client.get("/api/v1/proyectos/", headers=headers)
        assert list_response.status_code == 200
        assert all(p["id"] != project_id for p in list_response.json())

        # Verificar que aparece en /archived con deleted_at seteado
        archived_response = client.get("/api/v1/proyectos/archived", headers=headers)
        assert archived_response.status_code == 200
        archived = archived_response.json()
        assert len(archived) == 1
        assert archived[0]["id"] == project_id
        assert archived[0]["deleted_at"] is not None

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

    def test_search_projects_by_name(self):
        """Probar búsqueda de proyectos por nombre"""
        headers, _ = self.create_test_user_and_login()

        # Crear algunos proyectos
        projects_data = [
            {"name": "Proyecto Alpha"},
            {"name": "Proyecto Beta"},
            {"name": "Proyecto Gamma"},
            {"name": "Otro Proyecto"},
        ]

        for project_data in projects_data:
            response = client.post(
                "/api/v1/proyectos/", json=project_data, headers=headers
            )
            assert response.status_code == 201

        # Buscar proyectos que contengan 'Proyec'
        response = client.get("/api/v1/proyectos/search?query=Proyec", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 4

    def test_search_projects_no_match(self):
        """Probar búsqueda de proyectos con ningún resultado"""
        headers, _ = self.create_test_user_and_login()

        # Crear algunos proyectos
        projects_data = [
            {"name": "Proyecto Alpha"},
            {"name": "Proyecto Beta"},
        ]

        for project_data in projects_data:
            response = client.post(
                "/api/v1/proyectos/", json=project_data, headers=headers
            )
            assert response.status_code == 201

        # Buscar proyectos que contengan 'Delta' (no existe)
        response = client.get("/api/v1/proyectos/search?query=Delta", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_search_projects_case_insensitive(self):
        """Probar búsqueda de proyectos por nombre sin sensibilidad a mayúsculas/minúsculas"""
        headers, _ = self.create_test_user_and_login()

        # Crear algunos proyectos
        projects_data = [
            {"name": "Proyecto Alpha"},
            {"name": "proyecto beta"},
            {"name": "PROYECTO Gamma"},
        ]

        for project_data in projects_data:
            response = client.post(
                "/api/v1/proyectos/", json=project_data, headers=headers
            )
            assert response.status_code == 201

        # Buscar proyectos que contengan 'proyecto' en diferentes casos
        response = client.get(
            "/api/v1/proyectos/search?query=proyecto", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

    def test_delete_project_is_idempotent_when_archived(self):
        """Archivar un proyecto ya archivado sigue retornando 204"""
        headers, _ = self.create_test_user_and_login()

        create_response = client.post(
            "/api/v1/proyectos/", json={"name": "Proyecto Idempotente"}, headers=headers
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        first = client.delete(f"/api/v1/proyectos/{project_id}", headers=headers)
        assert first.status_code == 204

        second = client.delete(f"/api/v1/proyectos/{project_id}", headers=headers)
        assert second.status_code == 204

        archived = client.get("/api/v1/proyectos/archived", headers=headers)
        assert archived.status_code == 200
        assert len(archived.json()) == 1

    def test_list_projects_excludes_archived(self):
        """El listado general excluye archivados pero incluye activos"""
        headers, _ = self.create_test_user_and_login()

        ids = []
        for name in ["Proyecto Activo", "Proyecto A Archivar"]:
            resp = client.post(
                "/api/v1/proyectos/", json={"name": name}, headers=headers
            )
            assert resp.status_code == 201
            ids.append(resp.json()["id"])

        client.delete(f"/api/v1/proyectos/{ids[1]}", headers=headers)

        response = client.get("/api/v1/proyectos/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == ids[0]

    def test_archived_lists_only_owner_archived(self):
        """GET /archived lista solo los archivados del owner"""
        headers, _ = self.create_test_user_and_login()

        for name in ["Archivado 1", "Archivado 2", "Activo"]:
            resp = client.post(
                "/api/v1/proyectos/", json={"name": name}, headers=headers
            )
            assert resp.status_code == 201

        listed = client.get("/api/v1/proyectos/", headers=headers).json()
        to_archive = [p["id"] for p in listed if p["name"] != "Activo"]
        for pid in to_archive:
            assert (
                client.delete(f"/api/v1/proyectos/{pid}", headers=headers).status_code
                == 204
            )

        response = client.get("/api/v1/proyectos/archived", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert {p["name"] for p in data} == {"Archivado 1", "Archivado 2"}
        assert all(p["deleted_at"] is not None for p in data)

    def test_archived_empty_when_nothing_archived(self):
        """GET /archived retorna lista vacía si no hay archivados"""
        headers, _ = self.create_test_user_and_login()

        resp = client.post(
            "/api/v1/proyectos/", json={"name": "Solo Activo"}, headers=headers
        )
        assert resp.status_code == 201

        response = client.get("/api/v1/proyectos/archived", headers=headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_archived_does_not_leak_other_users(self):
        """Un usuario no ve los archivados de otro usuario"""
        headers1, _ = self.create_test_user_and_login()

        create_response = client.post(
            "/api/v1/proyectos/", json={"name": "Privado"}, headers=headers1
        )
        project_id = create_response.json()["id"]
        assert (
            client.delete(
                f"/api/v1/proyectos/{project_id}", headers=headers1
            ).status_code
            == 204
        )

        user_data_2 = {
            "email": "user2@example.com",
            "full_name": "User Two",
            "password": "Test123456",
            "phone_number": "+573001234568",
        }
        client.post("/api/v1/auth/register", json=user_data_2)
        login_response_2 = client.post(
            "/api/v1/auth/login",
            data={"username": "user2@example.com", "password": "Test123456"},
        )
        headers2 = {
            "Authorization": f"Bearer {login_response_2.json()['access_token']}"
        }

        response = client.get("/api/v1/proyectos/archived", headers=headers2)
        assert response.status_code == 200
        assert response.json() == []

    def test_get_archived_project_returns_404(self):
        """GET /{id}, /phases y /documentos de un archivado retornan 404"""
        headers, _ = self.create_test_user_and_login()

        create_response = client.post(
            "/api/v1/proyectos/", json={"name": "Se Archivará"}, headers=headers
        )
        project_id = create_response.json()["id"]
        assert (
            client.delete(
                f"/api/v1/proyectos/{project_id}", headers=headers
            ).status_code
            == 204
        )

        assert (
            client.get(f"/api/v1/proyectos/{project_id}", headers=headers).status_code
            == 404
        )
        assert (
            client.get(
                f"/api/v1/proyectos/{project_id}/phases", headers=headers
            ).status_code
            == 404
        )
        assert (
            client.get(
                f"/api/v1/proyectos/{project_id}/documentos", headers=headers
            ).status_code
            == 404
        )

    def test_search_excludes_archived(self):
        """La búsqueda excluye proyectos archivados"""
        headers, _ = self.create_test_user_and_login()

        for name in ["Alpha Buscable", "Alpha Archivado"]:
            resp = client.post(
                "/api/v1/proyectos/", json={"name": name}, headers=headers
            )
            assert resp.status_code == 201
            if name == "Alpha Archivado":
                assert (
                    client.delete(
                        f"/api/v1/proyectos/{resp.json()['id']}", headers=headers
                    ).status_code
                    == 204
                )

        response = client.get("/api/v1/proyectos/search?query=Alpha", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Alpha Buscable"

    def test_restore_project_success(self):
        """Restaurar un archivado lo vuelve accesible y lo saca de /archived"""
        headers, _ = self.create_test_user_and_login()

        create_response = client.post(
            "/api/v1/proyectos/", json={"name": "Restaurable"}, headers=headers
        )
        project_id = create_response.json()["id"]
        assert (
            client.delete(
                f"/api/v1/proyectos/{project_id}", headers=headers
            ).status_code
            == 204
        )

        response = client.post(
            f"/api/v1/proyectos/{project_id}/restore", headers=headers
        )
        assert response.status_code == 200
        assert response.json()["id"] == project_id
        assert response.json()["deleted_at"] is None

        assert (
            client.get(f"/api/v1/proyectos/{project_id}", headers=headers).status_code
            == 200
        )
        listed = client.get("/api/v1/proyectos/", headers=headers).json()
        assert any(p["id"] == project_id for p in listed)
        assert client.get("/api/v1/proyectos/archived", headers=headers).json() == []

    def test_restore_not_archived_returns_400(self):
        """Restaurar un proyecto activo retorna 400"""
        headers, _ = self.create_test_user_and_login()

        create_response = client.post(
            "/api/v1/proyectos/", json={"name": "Siempre Activo"}, headers=headers
        )
        project_id = create_response.json()["id"]

        response = client.post(
            f"/api/v1/proyectos/{project_id}/restore", headers=headers
        )
        assert response.status_code == 400

    def test_restore_not_found(self):
        """Restaurar un proyecto inexistente retorna 404"""
        headers, _ = self.create_test_user_and_login()

        response = client.post("/api/v1/proyectos/999999/restore", headers=headers)
        assert response.status_code == 404

    def test_restore_of_other_user_returns_404(self):
        """Restaurar un proyecto de otro usuario retorna 404"""
        headers1, _ = self.create_test_user_and_login()

        create_response = client.post(
            "/api/v1/proyectos/", json={"name": "Ajeno"}, headers=headers1
        )
        project_id = create_response.json()["id"]
        assert (
            client.delete(
                f"/api/v1/proyectos/{project_id}", headers=headers1
            ).status_code
            == 204
        )

        user_data_2 = {
            "email": "user2@example.com",
            "full_name": "User Two",
            "password": "Test123456",
            "phone_number": "+573001234568",
        }
        client.post("/api/v1/auth/register", json=user_data_2)
        login_response_2 = client.post(
            "/api/v1/auth/login",
            data={"username": "user2@example.com", "password": "Test123456"},
        )
        headers2 = {
            "Authorization": f"Bearer {login_response_2.json()['access_token']}"
        }

        response = client.post(
            f"/api/v1/proyectos/{project_id}/restore", headers=headers2
        )
        assert response.status_code == 404

        # El dueño todavía lo ve archivado
        archived = client.get("/api/v1/proyectos/archived", headers=headers1).json()
        assert any(p["id"] == project_id for p in archived)

    def test_permanent_delete_success(self):
        """El borrado permanente elimina un archivado de /archived"""
        headers, _ = self.create_test_user_and_login()

        create_response = client.post(
            "/api/v1/proyectos/", json={"name": "Borrado Total"}, headers=headers
        )
        project_id = create_response.json()["id"]
        assert (
            client.delete(
                f"/api/v1/proyectos/{project_id}", headers=headers
            ).status_code
            == 204
        )

        response = client.delete(
            f"/api/v1/proyectos/{project_id}/permanent", headers=headers
        )
        assert response.status_code == 204

        assert client.get("/api/v1/proyectos/archived", headers=headers).json() == []
        assert (
            client.post(
                f"/api/v1/proyectos/{project_id}/restore", headers=headers
            ).status_code
            == 404
        )

    def test_permanent_delete_not_archived_returns_400(self):
        """El borrado permanente de un activo retorna 400 y lo conserva"""
        headers, _ = self.create_test_user_and_login()

        create_response = client.post(
            "/api/v1/proyectos/", json={"name": "No Archivado"}, headers=headers
        )
        project_id = create_response.json()["id"]

        response = client.delete(
            f"/api/v1/proyectos/{project_id}/permanent", headers=headers
        )
        assert response.status_code == 400

        assert (
            client.get(f"/api/v1/proyectos/{project_id}", headers=headers).status_code
            == 200
        )

    def test_permanent_delete_not_found(self):
        """El borrado permanente de un inexistente retorna 404"""
        headers, _ = self.create_test_user_and_login()

        response = client.delete("/api/v1/proyectos/999999/permanent", headers=headers)
        assert response.status_code == 404

    def test_permanent_delete_of_other_user_returns_404(self):
        """El borrado permanente de un proyecto ajeno retorna 404 y lo conserva"""
        headers1, _ = self.create_test_user_and_login()

        create_response = client.post(
            "/api/v1/proyectos/", json={"name": "Ajeno Permanente"}, headers=headers1
        )
        project_id = create_response.json()["id"]
        assert (
            client.delete(
                f"/api/v1/proyectos/{project_id}", headers=headers1
            ).status_code
            == 204
        )

        user_data_2 = {
            "email": "user2@example.com",
            "full_name": "User Two",
            "password": "Test123456",
            "phone_number": "+573001234568",
        }
        client.post("/api/v1/auth/register", json=user_data_2)
        login_response_2 = client.post(
            "/api/v1/auth/login",
            data={"username": "user2@example.com", "password": "Test123456"},
        )
        headers2 = {
            "Authorization": f"Bearer {login_response_2.json()['access_token']}"
        }

        response = client.delete(
            f"/api/v1/proyectos/{project_id}/permanent", headers=headers2
        )
        assert response.status_code == 404

        archived = client.get("/api/v1/proyectos/archived", headers=headers1).json()
        assert any(p["id"] == project_id for p in archived)
