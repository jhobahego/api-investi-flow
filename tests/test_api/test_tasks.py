from datetime import datetime, timezone
from io import BytesIO

import pytest

from app.database import Base
from tests.test_db_config import client, engine


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestTaskEndpoints:
    """Pruebas para los endpoints de tareas"""

    def create_test_user_and_login(
        self, email="testuser@example.com", phone_number=None
    ):
        """Helper para crear un usuario de prueba y hacer login"""

        # Generar un número de teléfono único basado en el email si no se proporciona
        if phone_number is None:
            phone_suffix = str(abs(hash(email)) % 10000).zfill(4)
            phone_number = f"+57300123{phone_suffix}"

        user_data = {
            "email": email,
            "full_name": "Test User",
            "password": "Test123456",
            "phone_number": phone_number,
        }

        # Crear usuario
        register_response = client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201

        # Hacer login
        login_data = {"username": email, "password": "Test123456"}
        login_response = client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        user_id = register_response.json()["id"]

        return headers, user_id

    def create_test_project(self, headers):
        """Helper para crear un proyecto de prueba"""
        project_data = {
            "name": "Proyecto de Prueba para Tareas",
            "description": "Este es un proyecto de prueba para las tareas",
        }

        response = client.post("/api/v1/proyectos/", json=project_data, headers=headers)
        assert response.status_code == 201
        return response.json()

    def create_test_phase(self, headers, project_id):
        """Helper para crear una fase de prueba"""
        phase_data = {
            "name": "Fase de Prueba para Tareas",
            "position": 0,
            "project_id": project_id,
        }

        response = client.post("/api/v1/fases/", json=phase_data, headers=headers)
        assert response.status_code == 201
        return response.json()

    def test_create_task_success(self):
        """Probar creación exitosa de tarea"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        task_data = {
            "title": "Tarea de Análisis de Requisitos",
            "description": "Analizar los requisitos del sistema",
            "position": 0,
            "status": "pending",
            "phase_id": phase["id"],
        }

        response = client.post("/api/v1/tareas/", json=task_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == task_data["title"]
        assert data["description"] == task_data["description"]
        assert data["position"] == task_data["position"]
        assert data["status"] == task_data["status"]
        assert data["phase_id"] == task_data["phase_id"]
        assert data["completed"] is False
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_task_minimal_data(self):
        """Probar creación de tarea con datos mínimos"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        task_data = {
            "title": "Tarea Mínima de Prueba",
            "position": 0,
            "phase_id": phase["id"],
        }

        response = client.post("/api/v1/tareas/", json=task_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == task_data["title"]
        assert data["description"] is None
        assert data["position"] == task_data["position"]
        assert data["status"] == "pending"  # Valor por defecto
        assert data["completed"] is False
        assert data["start_date"] is None
        assert data["end_date"] is None

    def test_create_task_with_dates(self):
        """Probar creación de tarea con fechas"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        start_date = datetime.now(timezone.utc).isoformat()
        end_date = datetime.now(timezone.utc).replace(hour=23, minute=59).isoformat()

        task_data = {
            "title": "Tarea con Fechas de Prueba",
            "description": "Tarea que tiene fechas de inicio y fin",
            "position": 0,
            "phase_id": phase["id"],
            "start_date": start_date,
            "end_date": end_date,
        }

        response = client.post("/api/v1/tareas/", json=task_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["start_date"] is not None
        assert data["end_date"] is not None

    def test_create_task_without_authentication(self):
        """Probar creación de tarea sin autenticación"""
        task_data = {
            "title": "Tarea Sin Autenticación",
            "position": 0,
            "phase_id": 1,
        }

        response = client.post("/api/v1/tareas/", json=task_data)

        assert response.status_code == 401

    def test_create_task_invalid_phase(self):
        """Probar creación de tarea con fase inexistente"""
        headers, user_id = self.create_test_user_and_login()

        task_data = {
            "title": "Tarea de Fase Inexistente",
            "position": 0,
            "phase_id": 999999,
        }

        response = client.post("/api/v1/tareas/", json=task_data, headers=headers)

        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"]

    def test_create_task_phase_of_other_user(self):
        """Probar creación de tarea en fase de otro usuario"""
        # Crear primer usuario, proyecto y fase
        headers1, user_id1 = self.create_test_user_and_login("user1@example.com")
        project = self.create_test_project(headers1)
        phase = self.create_test_phase(headers1, project["id"])

        # Crear segundo usuario
        headers2, user_id2 = self.create_test_user_and_login("user2@example.com")

        # Intentar crear tarea en fase del primer usuario
        task_data = {
            "title": "Tarea en Fase Ajena",
            "position": 0,
            "phase_id": phase["id"],
        }

        response = client.post("/api/v1/tareas/", json=task_data, headers=headers2)

        assert response.status_code == 404
        assert (
            "No tienes permisos para crear tareas en esta fase"
            in response.json()["detail"]
        )

    def test_create_task_invalid_title(self):
        """Probar creación de tarea con título inválido"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        # Título muy corto
        task_data = {
            "title": "ABC",
            "position": 0,
            "phase_id": phase["id"],
        }

        response = client.post("/api/v1/tareas/", json=task_data, headers=headers)

        assert response.status_code == 422

        # Título vacío
        task_data["title"] = ""
        response = client.post("/api/v1/tareas/", json=task_data, headers=headers)

        assert response.status_code == 422

        # Título solo espacios
        task_data["title"] = "     "
        response = client.post("/api/v1/tareas/", json=task_data, headers=headers)

        assert response.status_code == 422

    def test_create_task_invalid_dates(self):
        """Probar creación de tarea con fechas inválidas"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        # Fecha de fin anterior a fecha de inicio
        start_date = datetime.now(timezone.utc).isoformat()
        end_date = datetime.now(timezone.utc).replace(hour=0, minute=0).isoformat()

        task_data = {
            "title": "Tarea con Fechas Inválidas",
            "position": 0,
            "phase_id": phase["id"],
            "start_date": start_date,
            "end_date": end_date,
        }

        response = client.post("/api/v1/tareas/", json=task_data, headers=headers)

        assert response.status_code == 422

    def test_create_task_negative_position(self):
        """Probar creación de tarea con posición negativa"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        task_data = {
            "title": "Tarea con Posición Negativa",
            "position": -1,
            "phase_id": phase["id"],
        }

        response = client.post("/api/v1/tareas/", json=task_data, headers=headers)

        assert response.status_code == 422

    def test_get_tasks_by_phase_success(self):
        """Probar obtener tareas por fase exitosamente"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        # Crear varias tareas
        task_titles = ["Primera Tarea", "Segunda Tarea", "Tercera Tarea"]
        created_tasks = []

        for i, title in enumerate(task_titles):
            task_data = {
                "title": title,
                "position": i,
                "phase_id": phase["id"],
            }
            response = client.post("/api/v1/tareas/", json=task_data, headers=headers)
            assert response.status_code == 201
            created_tasks.append(response.json())

        # Obtener tareas de la fase
        response = client.get(
            f"/api/v1/tareas/?phase_id={phase['id']}", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        # Verificar que las tareas están ordenadas por posición
        for i, task in enumerate(data):
            assert task["title"] == task_titles[i]
            assert task["position"] == i

    def test_get_tasks_by_phase_empty(self):
        """Probar obtener tareas de fase vacía"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        response = client.get(
            f"/api/v1/tareas/?phase_id={phase['id']}", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_get_tasks_by_phase_without_authentication(self):
        """Probar obtener tareas sin autenticación"""
        response = client.get("/api/v1/tareas/?phase_id=1")

        assert response.status_code == 401

    def test_get_tasks_by_phase_invalid_phase(self):
        """Probar obtener tareas de fase inexistente"""
        headers, user_id = self.create_test_user_and_login()

        response = client.get("/api/v1/tareas/?phase_id=999999", headers=headers)

        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"]

    def test_get_tasks_by_phase_of_other_user(self):
        """Probar obtener tareas de fase de otro usuario"""
        # Crear primer usuario, proyecto y fase
        headers1, user_id1 = self.create_test_user_and_login("user1@example.com")
        project = self.create_test_project(headers1)
        phase = self.create_test_phase(headers1, project["id"])

        # Crear segundo usuario
        headers2, user_id2 = self.create_test_user_and_login("user2@example.com")

        # Intentar obtener tareas de fase del primer usuario
        response = client.get(
            f"/api/v1/tareas/?phase_id={phase['id']}", headers=headers2
        )

        assert response.status_code == 404
        assert (
            "No tienes permisos para acceder a las tareas de esta fase"
            in response.json()["detail"]
        )

    def test_update_task_success(self):
        """Probar actualización exitosa de tarea"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        # Crear tarea
        task_data = {
            "title": "Tarea Original",
            "description": "Descripción original",
            "position": 0,
            "phase_id": phase["id"],
        }

        create_response = client.post(
            "/api/v1/tareas/", json=task_data, headers=headers
        )
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        # Actualizar la tarea
        update_data = {
            "title": "Tarea Actualizada",
            "description": "Descripción actualizada",
            "status": "in_progress",
            "completed": True,
        }

        response = client.put(
            f"/api/v1/tareas/{task_id}", json=update_data, headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["title"] == update_data["title"]
        assert data["description"] == update_data["description"]
        assert data["status"] == update_data["status"]
        assert data["completed"] == update_data["completed"]
        assert data["position"] == 0  # No cambiada

    def test_update_task_partial(self):
        """Probar actualización parcial de tarea"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        # Crear tarea
        task_data = {
            "title": "Tarea para Actualización Parcial",
            "description": "Descripción original",
            "position": 0,
            "phase_id": phase["id"],
            "status": "pending",
        }

        create_response = client.post(
            "/api/v1/tareas/", json=task_data, headers=headers
        )
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        # Actualizar solo el estado
        update_data = {"status": "completed"}

        response = client.put(
            f"/api/v1/tareas/{task_id}", json=update_data, headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["title"] == task_data["title"]  # Sin cambios
        assert data["description"] == task_data["description"]  # Sin cambios

    def test_update_task_dates(self):
        """Probar actualización de fechas de tarea"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        # Crear tarea
        task_data = {
            "title": "Tarea con Fechas para Actualizar",
            "position": 0,
            "phase_id": phase["id"],
        }

        create_response = client.post(
            "/api/v1/tareas/", json=task_data, headers=headers
        )
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        # Actualizar fechas
        start_date = datetime.now(timezone.utc).isoformat()
        end_date = datetime.now(timezone.utc).replace(hour=23, minute=59).isoformat()

        update_data = {
            "start_date": start_date,
            "end_date": end_date,
        }

        response = client.put(
            f"/api/v1/tareas/{task_id}", json=update_data, headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["start_date"] is not None
        assert data["end_date"] is not None

    def test_update_task_not_found(self):
        """Probar actualización de tarea que no existe"""
        headers, user_id = self.create_test_user_and_login()

        update_data = {"title": "Tarea Inexistente"}

        response = client.put(
            "/api/v1/tareas/999999", json=update_data, headers=headers
        )

        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"]

    def test_update_task_of_other_user(self):
        """Probar actualizar tarea de otro usuario"""
        # Crear primer usuario, proyecto, fase y tarea
        headers1, user_id1 = self.create_test_user_and_login("user1@example.com")
        project = self.create_test_project(headers1)
        phase = self.create_test_phase(headers1, project["id"])

        task_data = {
            "title": "Tarea Usuario 1",
            "position": 0,
            "phase_id": phase["id"],
        }

        create_response = client.post(
            "/api/v1/tareas/", json=task_data, headers=headers1
        )
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        # Crear segundo usuario
        headers2, user_id2 = self.create_test_user_and_login("user2@example.com")

        # Intentar actualizar la tarea del primer usuario
        update_data = {"title": "Intento de Hackeo"}
        response = client.put(
            f"/api/v1/tareas/{task_id}", json=update_data, headers=headers2
        )

        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"]

    def test_update_task_invalid_title(self):
        """Probar actualización con título inválido"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        # Crear tarea
        task_data = {
            "title": "Tarea para Actualización Inválida",
            "position": 0,
            "phase_id": phase["id"],
        }

        create_response = client.post(
            "/api/v1/tareas/", json=task_data, headers=headers
        )
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        # Intentar actualizar con título muy corto
        update_data = {"title": "AB"}

        response = client.put(
            f"/api/v1/tareas/{task_id}", json=update_data, headers=headers
        )

        assert response.status_code == 422

    def test_update_task_invalid_dates(self):
        """Probar actualización con fechas inválidas"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        # Crear tarea
        task_data = {
            "title": "Tarea para Fechas Inválidas",
            "position": 0,
            "phase_id": phase["id"],
        }

        create_response = client.post(
            "/api/v1/tareas/", json=task_data, headers=headers
        )
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        # Intentar actualizar con fecha de fin anterior a fecha de inicio
        start_date = datetime.now(timezone.utc).isoformat()
        end_date = datetime.now(timezone.utc).replace(hour=0, minute=0).isoformat()

        update_data = {
            "start_date": start_date,
            "end_date": end_date,
        }

        response = client.put(
            f"/api/v1/tareas/{task_id}", json=update_data, headers=headers
        )

        assert response.status_code == 422

    def test_delete_task_success(self):
        """Probar eliminación exitosa de tarea"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        # Crear tarea
        task_data = {
            "title": "Tarea a Eliminar",
            "position": 0,
            "phase_id": phase["id"],
        }

        create_response = client.post(
            "/api/v1/tareas/", json=task_data, headers=headers
        )
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        # Eliminar la tarea
        response = client.delete(f"/api/v1/tareas/{task_id}", headers=headers)

        assert response.status_code == 204

        # Verificar que la tarea ya no existe en la lista de tareas de la fase
        get_response = client.get(
            f"/api/v1/tareas/?phase_id={phase['id']}", headers=headers
        )
        assert get_response.status_code == 200
        tasks = get_response.json()
        assert len(tasks) == 0

    def test_delete_task_not_found(self):
        """Probar eliminación de tarea que no existe"""
        headers, user_id = self.create_test_user_and_login()

        response = client.delete("/api/v1/tareas/999999", headers=headers)

        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"]

    def test_delete_task_of_other_user(self):
        """Probar eliminar tarea de otro usuario"""
        # Crear primer usuario, proyecto, fase y tarea
        headers1, user_id1 = self.create_test_user_and_login("user1@example.com")
        project = self.create_test_project(headers1)
        phase = self.create_test_phase(headers1, project["id"])

        task_data = {
            "title": "Tarea Usuario 1",
            "position": 0,
            "phase_id": phase["id"],
        }

        create_response = client.post(
            "/api/v1/tareas/", json=task_data, headers=headers1
        )
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        # Crear segundo usuario
        headers2, user_id2 = self.create_test_user_and_login("user2@example.com")

        # Intentar eliminar la tarea del primer usuario
        response = client.delete(f"/api/v1/tareas/{task_id}", headers=headers2)

        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"]

        # Verificar que la tarea sigue existiendo para el primer usuario
        get_response = client.get(
            f"/api/v1/tareas/?phase_id={phase['id']}", headers=headers1
        )
        assert get_response.status_code == 200
        tasks = get_response.json()
        assert len(tasks) == 1

    def test_upload_document_success(self):
        """Probar subida exitosa de documento a tarea"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        # Crear tarea
        task_data = {
            "title": "Tarea con Documento",
            "position": 0,
            "phase_id": phase["id"],
        }

        create_response = client.post(
            "/api/v1/tareas/", json=task_data, headers=headers
        )
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        # Crear archivo de prueba (PDF válido)
        file_content = b"Contenido del documento de prueba"
        file_data = {
            "file": ("test_document.pdf", BytesIO(file_content), "application/pdf")
        }

        # Subir documento
        response = client.post(
            f"/api/v1/tareas/{task_id}/documentos", files=file_data, headers=headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["file_name"] == "test_document.pdf"
        assert data["file_type"] == "pdf"  # El servicio retorna solo la extensión
        assert data["task_id"] == task_id
        assert data["project_id"] is None
        assert data["phase_id"] is None
        assert "id" in data
        assert "file_path" in data

    def test_upload_document_without_authentication(self):
        """Probar subida de documento sin autenticación"""
        file_content = b"Contenido del documento de prueba"
        file_data = {
            "file": ("test_document.pdf", BytesIO(file_content), "application/pdf")
        }

        response = client.post("/api/v1/tareas/1/documentos", files=file_data)

        assert response.status_code == 401

    def test_upload_document_task_not_found(self):
        """Probar subida de documento a tarea inexistente"""
        headers, user_id = self.create_test_user_and_login()

        file_content = b"Contenido del documento de prueba"
        file_data = {
            "file": ("test_document.pdf", BytesIO(file_content), "application/pdf")
        }

        response = client.post(
            "/api/v1/tareas/999999/documentos", files=file_data, headers=headers
        )

        assert response.status_code == 404

    def test_upload_document_task_of_other_user(self):
        """Probar subida de documento a tarea de otro usuario"""
        # Crear primer usuario, proyecto, fase y tarea
        headers1, user_id1 = self.create_test_user_and_login("user1@example.com")
        project = self.create_test_project(headers1)
        phase = self.create_test_phase(headers1, project["id"])

        task_data = {
            "title": "Tarea Usuario 1",
            "position": 0,
            "phase_id": phase["id"],
        }

        create_response = client.post(
            "/api/v1/tareas/", json=task_data, headers=headers1
        )
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        # Crear segundo usuario
        headers2, user_id2 = self.create_test_user_and_login("user2@example.com")

        # Intentar subir documento a tarea del primer usuario
        file_content = b"Contenido del documento de prueba"
        file_data = {
            "file": ("test_document.pdf", BytesIO(file_content), "application/pdf")
        }

        response = client.post(
            f"/api/v1/tareas/{task_id}/documentos", files=file_data, headers=headers2
        )

        assert response.status_code == 403

    def test_upload_document_invalid_file_type(self):
        """Probar subida de documento con tipo de archivo no permitido"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        # Crear tarea
        task_data = {
            "title": "Tarea para Archivo Inválido",
            "position": 0,
            "phase_id": phase["id"],
        }

        create_response = client.post(
            "/api/v1/tareas/", json=task_data, headers=headers
        )
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        # Intentar subir archivo con extensión no permitida (.txt)
        file_content = b"Contenido del documento de prueba"
        file_data = {"file": ("test_document.txt", BytesIO(file_content), "text/plain")}

        response = client.post(
            f"/api/v1/tareas/{task_id}/documentos", files=file_data, headers=headers
        )

        assert response.status_code == 400
        assert "Tipo de archivo no permitido" in response.json()["detail"]
        assert "Extensiones permitidas: .pdf, .docx, .doc" in response.json()["detail"]

    def test_get_task_document_success(self):
        """Probar obtener documento de tarea exitosamente"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        # Crear tarea
        task_data = {
            "title": "Tarea con Documento para Obtener",
            "position": 0,
            "phase_id": phase["id"],
        }

        create_response = client.post(
            "/api/v1/tareas/", json=task_data, headers=headers
        )
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        # Subir documento
        file_content = b"Contenido del documento de prueba"
        file_data = {
            "file": ("test_document.pdf", BytesIO(file_content), "application/pdf")
        }

        upload_response = client.post(
            f"/api/v1/tareas/{task_id}/documentos", files=file_data, headers=headers
        )
        assert upload_response.status_code == 201

        # Obtener documento
        response = client.get(f"/api/v1/tareas/{task_id}/documentos", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["file_name"] == "test_document.pdf"
        assert data["file_type"] == "pdf"  # El servicio retorna solo la extensión
        assert data["task_id"] == task_id

    def test_get_task_document_not_found(self):
        """Probar obtener documento de tarea sin documento"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        # Crear tarea sin documento
        task_data = {
            "title": "Tarea Sin Documento",
            "position": 0,
            "phase_id": phase["id"],
        }

        create_response = client.post(
            "/api/v1/tareas/", json=task_data, headers=headers
        )
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        # Intentar obtener documento
        response = client.get(f"/api/v1/tareas/{task_id}/documentos", headers=headers)

        assert response.status_code == 200
        assert response.json() is None

    def test_get_task_document_without_authentication(self):
        """Probar obtener documento de tarea sin autenticación"""
        response = client.get("/api/v1/tareas/1/documentos")

        assert response.status_code == 401

    def test_get_task_document_task_not_found(self):
        """Probar obtener documento de tarea inexistente"""
        headers, user_id = self.create_test_user_and_login()

        response = client.get("/api/v1/tareas/999999/documentos", headers=headers)

        assert response.status_code == 404

    def test_get_task_document_task_of_other_user(self):
        """Probar obtener documento de tarea de otro usuario"""
        # Crear primer usuario, proyecto, fase y tarea con documento
        headers1, user_id1 = self.create_test_user_and_login("user1@example.com")
        project = self.create_test_project(headers1)
        phase = self.create_test_phase(headers1, project["id"])

        task_data = {
            "title": "Tarea Usuario 1 con Documento",
            "position": 0,
            "phase_id": phase["id"],
        }

        create_response = client.post(
            "/api/v1/tareas/", json=task_data, headers=headers1
        )
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        # Subir documento
        file_content = b"Contenido del documento de prueba"
        file_data = {
            "file": ("test_document.pdf", BytesIO(file_content), "application/pdf")
        }

        upload_response = client.post(
            f"/api/v1/tareas/{task_id}/documentos", files=file_data, headers=headers1
        )
        assert upload_response.status_code == 201

        # Crear segundo usuario
        headers2, user_id2 = self.create_test_user_and_login("user2@example.com")

        # Intentar obtener documento de tarea del primer usuario
        response = client.get(f"/api/v1/tareas/{task_id}/documentos", headers=headers2)

        assert response.status_code == 403  # Forbidden, no 404

    def test_task_validation_missing_required_fields(self):
        """Probar validación de campos requeridos faltantes"""
        headers, user_id = self.create_test_user_and_login()

        # Sin título
        task_data = {
            "position": 0,
            "phase_id": 1,
        }

        response = client.post("/api/v1/tareas/", json=task_data, headers=headers)

        assert response.status_code == 422

        # Sin phase_id
        task_data = {
            "title": "Tarea sin fase",
            "position": 0,
        }

        response = client.post("/api/v1/tareas/", json=task_data, headers=headers)

        assert response.status_code == 422

        # Sin position
        task_data = {
            "title": "Tarea sin posición",
            "phase_id": 1,
        }

        response = client.post("/api/v1/tareas/", json=task_data, headers=headers)

        assert response.status_code == 422

    def test_task_status_validation(self):
        """Probar validación de estados de tarea"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        # Estado válido
        valid_statuses = ["pending", "in_progress", "completed", "on_hold"]

        for status in valid_statuses:
            task_data = {
                "title": f"Tarea con Estado {status}",
                "position": 0,
                "phase_id": phase["id"],
                "status": status,
            }

            response = client.post("/api/v1/tareas/", json=task_data, headers=headers)
            assert response.status_code == 201

        # Estado inválido
        task_data = {
            "title": "Tarea con Estado Inválido",
            "position": 0,
            "phase_id": phase["id"],
            "status": "invalid_status",
        }

        response = client.post("/api/v1/tareas/", json=task_data, headers=headers)
        assert response.status_code == 422

    def test_task_endpoints_without_authentication(self):
        """Probar todos los endpoints sin autenticación"""
        # POST crear tarea
        response = client.post(
            "/api/v1/tareas/", json={"title": "Test", "position": 0, "phase_id": 1}
        )
        assert response.status_code == 401

        # GET obtener tareas por fase
        response = client.get("/api/v1/tareas/?phase_id=1")
        assert response.status_code == 401

        # PUT actualizar tarea
        response = client.put("/api/v1/tareas/1", json={"title": "Nueva Tarea"})
        assert response.status_code == 401

        # DELETE eliminar tarea
        response = client.delete("/api/v1/tareas/1")
        assert response.status_code == 401

        # POST subir documento
        file_data = {"file": ("test.pdf", BytesIO(b"test"), "application/pdf")}
        response = client.post("/api/v1/tareas/1/documentos", files=file_data)
        assert response.status_code == 401

        # GET obtener documento
        response = client.get("/api/v1/tareas/1/documentos")
        assert response.status_code == 401
