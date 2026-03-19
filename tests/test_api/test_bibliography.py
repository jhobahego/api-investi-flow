import os

import pytest

from app.database import Base
from tests.test_db_config import client, engine


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestBibliographyEndpoints:
    """Pruebas para los endpoints de bibliografía"""

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
        if register_response.status_code != 201:
            # Si ya existe, intentar login
            pass

        # Hacer login
        login_data = {"username": "testuser@example.com", "password": "Test123456"}
        login_response = client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Obtener ID de usuario (si se creó o ya existía)
        if register_response.status_code == 201:
            user_id = register_response.json()["id"]
        else:
            # Obtener perfil para sacar ID
            profile = client.get("/api/v1/users/me", headers=headers)
            user_id = profile.json()["id"]

        return headers, user_id

    def create_test_project(self, headers):
        """Helper para crear un proyecto de prueba"""
        project_data = {
            "name": "Proyecto Bibliografía",
            "description": "Proyecto para probar bibliografías",
            "research_type": "experimental",
        }
        response = client.post("/api/v1/proyectos/", json=project_data, headers=headers)
        assert response.status_code == 201
        return response.json()["id"]

    def test_create_bibliography_success(self):
        """Probar creación exitosa de bibliografía"""
        headers, _ = self.create_test_user_and_login()
        project_id = self.create_test_project(headers)

        bib_data = {
            "type": "libro",
            "author": "García, M.",
            "year": 2023,
            "title": "Investigación Avanzada",
            "source": "Editorial Test",
            "doi": "10.1234/test",
            "url": "http://example.com",
        }

        response = client.post(
            f"/api/v1/proyectos/{project_id}/bibliografias",
            json=bib_data,
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == bib_data["title"]
        assert data["author"] == bib_data["author"]
        assert data["project_id"] == project_id
        assert "id" in data

    def test_list_bibliographies(self):
        """Probar listado de bibliografías"""
        headers, _ = self.create_test_user_and_login()
        project_id = self.create_test_project(headers)

        # Crear 2 bibliografías
        bib_data_1 = {
            "type": "libro",
            "author": "Autor 1",
            "title": "Libro 1",
            "year": 2020,
        }
        bib_data_2 = {
            "type": "articulo",
            "author": "Autor 2",
            "title": "Articulo 1",
            "year": 2021,
        }

        client.post(
            f"/api/v1/proyectos/{project_id}/bibliografias",
            json=bib_data_1,
            headers=headers,
        )
        client.post(
            f"/api/v1/proyectos/{project_id}/bibliografias",
            json=bib_data_2,
            headers=headers,
        )

        # Listar
        response = client.get(
            f"/api/v1/proyectos/{project_id}/bibliografias", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "Libro 1"
        assert data[1]["title"] == "Articulo 1"

    def test_update_bibliography(self):
        """Probar actualización de bibliografía"""
        headers, _ = self.create_test_user_and_login()
        project_id = self.create_test_project(headers)

        # Crear
        bib_data = {
            "type": "libro",
            "author": "Autor Original",
            "title": "Titulo Original",
            "year": 2020,
        }
        create_res = client.post(
            f"/api/v1/proyectos/{project_id}/bibliografias",
            json=bib_data,
            headers=headers,
        )
        bib_id = create_res.json()["id"]

        # Actualizar
        update_data = {"title": "Titulo Actualizado", "year": 2025}
        response = client.put(
            f"/api/v1/proyectos/{project_id}/bibliografias/{bib_id}",
            json=update_data,
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Titulo Actualizado"
        assert data["year"] == 2025
        assert data["author"] == "Autor Original"  # No cambió

    def test_delete_bibliography(self):
        """Probar eliminación de bibliografía"""
        headers, _ = self.create_test_user_and_login()
        project_id = self.create_test_project(headers)

        # Crear
        bib_data = {
            "type": "libro",
            "author": "Autor Borrar",
            "title": "Titulo Borrar",
            "year": 2020,
        }
        create_res = client.post(
            f"/api/v1/proyectos/{project_id}/bibliografias",
            json=bib_data,
            headers=headers,
        )
        bib_id = create_res.json()["id"]

        # Eliminar
        response = client.delete(
            f"/api/v1/proyectos/{project_id}/bibliografias/{bib_id}", headers=headers
        )
        assert response.status_code == 204

        # Verificar que no existe
        list_res = client.get(
            f"/api/v1/proyectos/{project_id}/bibliografias", headers=headers
        )
        assert len(list_res.json()) == 0

    def test_access_denied_other_user(self):
        """Probar que otro usuario no puede acceder a bibliografías"""
        # Usuario 1
        headers1, _ = self.create_test_user_and_login()
        project_id = self.create_test_project(headers1)

        # Usuario 2
        user_data_2 = {
            "email": "user2_bib@example.com",
            "full_name": "User Two",
            "password": "Test123456",
            "phone_number": "+573001234569",
        }
        client.post("/api/v1/auth/register", json=user_data_2)
        login_res = client.post(
            "/api/v1/auth/login",
            data={"username": "user2_bib@example.com", "password": "Test123456"},
        )
        token2 = login_res.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Intentar listar bibliografías del proyecto de usuario 1
        response = client.get(
            f"/api/v1/proyectos/{project_id}/bibliografias", headers=headers2
        )
        assert (
            response.status_code == 404
        )  # O 403 dependiendo de la implementación de verify_project_access
