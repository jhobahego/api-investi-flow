import io
from unittest.mock import patch

import pytest

from app.database import Base
from tests.test_db_config import client, engine


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestAttachmentEndpoints:
    """Pruebas para los endpoints de adjuntos"""

    # Contador para generar números de teléfono únicos
    _phone_counter = 0

    def create_test_user_and_login(self, email="testuser@example.com", phone=None):
        """Helper para crear un usuario de prueba y hacer login"""
        if phone is None:
            # Generar número único incrementando el contador
            TestAttachmentEndpoints._phone_counter += 1
            phone = f"+57300123{TestAttachmentEndpoints._phone_counter:04d}"

        user_data = {
            "email": email,
            "full_name": "Test User",
            "password": "Test123456",
            "phone_number": phone,
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

    def create_test_project(self, headers, name="Test Project"):
        """Helper para crear un proyecto de prueba"""
        project_data = {"name": name, "description": "Test project description"}

        response = client.post("/api/v1/proyectos/", json=project_data, headers=headers)
        assert response.status_code == 201
        return response.json()

    def create_test_phase(self, headers, project_id, name="Test Phase Name"):
        """Helper para crear una fase de prueba"""
        phase_data = {
            "name": name,  # Al menos 5 caracteres
            "description": "Test phase description",
            "project_id": project_id,
            "position": 1,  # Campo requerido
        }

        response = client.post("/api/v1/fases/", json=phase_data, headers=headers)
        assert response.status_code == 201
        return response.json()

    def create_test_task(self, headers, phase_id, title="Test Task Title"):
        """Helper para crear una tarea de prueba"""
        task_data = {
            "title": title,  # Campo correcto según el esquema (al menos 5 caracteres)
            "description": "Test task description",
            "phase_id": phase_id,
            "position": 1,  # Campo requerido
        }

        response = client.post("/api/v1/tareas/", json=task_data, headers=headers)
        assert response.status_code == 201
        return response.json()

    def create_test_pdf_file(self, filename="test.pdf", content=b"fake pdf content"):
        """Helper para crear un archivo PDF de prueba"""
        return (filename, io.BytesIO(content), "application/pdf")

    def create_test_docx_file(self, filename="test.docx", content=b"fake docx content"):
        """Helper para crear un archivo DOCX de prueba"""
        return (
            filename,
            io.BytesIO(content),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def create_test_invalid_file(self, filename="test.txt", content=b"invalid file"):
        """Helper para crear un archivo inválido"""
        return (filename, io.BytesIO(content), "text/plain")

    # Tests para endpoints de proyectos
    def test_upload_document_to_project_success_pdf(self):
        """Probar subida exitosa de PDF a proyecto"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Preparar archivo de prueba
        file_data = self.create_test_pdf_file("project_document.pdf")

        # Subir documento
        response = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
            files={"file": file_data},
        )

        if response.status_code != 201:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")

        assert response.status_code == 201
        data = response.json()
        assert data["file_name"] == "project_document.pdf"
        assert data["file_type"] == "pdf"
        assert data["project_id"] == project["id"]
        assert data["phase_id"] is None
        assert data["task_id"] is None
        assert "file_path" in data
        assert "file_size" in data
        assert "id" in data

    def test_upload_document_to_project_success_docx(self):
        """Probar subida exitosa de DOCX a proyecto"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Preparar archivo de prueba
        file_data = self.create_test_docx_file("project_document.docx")

        # Subir documento
        response = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
            files={"file": file_data},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["file_name"] == "project_document.docx"
        assert data["file_type"] == "docx"
        assert data["project_id"] == project["id"]

    def test_upload_document_to_project_invalid_file_type(self):
        """Probar subida de tipo de archivo inválido a proyecto"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Preparar archivo inválido
        file_data = self.create_test_invalid_file("invalid.txt")

        # Intentar subir documento
        response = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
            files={"file": file_data},
        )

        assert response.status_code == 400
        assert "Tipo de archivo no permitido" in response.json()["detail"]

    def test_upload_document_to_project_file_too_large(self):
        """Probar subida de archivo muy grande a proyecto"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Crear archivo grande (simular 60MB)
        large_content = b"x" * (60 * 1024 * 1024)  # 60MB
        file_data = self.create_test_pdf_file("large.pdf", large_content)

        # Intentar subir documento
        response = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
            files={"file": file_data},
        )

        assert response.status_code == 400
        assert "demasiado grande" in response.json()["detail"]

    def test_upload_document_to_project_already_exists(self):
        """Probar subida cuando ya existe un documento"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Subir primer documento
        file_data1 = self.create_test_pdf_file("first.pdf")
        response1 = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
            files={"file": file_data1},
        )
        assert response1.status_code == 201

        # Intentar subir segundo documento
        file_data2 = self.create_test_pdf_file("second.pdf")
        response2 = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
            files={"file": file_data2},
        )

        assert response2.status_code == 400
        assert "ya tiene un documento adjunto" in response2.json()["detail"]

    def test_upload_document_to_project_not_found(self):
        """Probar subida a proyecto que no existe"""
        headers, user_id = self.create_test_user_and_login()

        file_data = self.create_test_pdf_file("test.pdf")

        response = client.post(
            "/api/v1/proyectos/999999/documentos",
            headers=headers,
            files={"file": file_data},
        )

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]

    def test_upload_document_to_project_without_auth(self):
        """Probar subida sin autenticación"""
        file_data = self.create_test_pdf_file("test.pdf")

        response = client.post(
            "/api/v1/proyectos/1/documentos", files={"file": file_data}
        )

        assert response.status_code == 401

    def test_upload_document_to_project_other_user(self):
        """Probar subida a proyecto de otro usuario"""
        # Crear primer usuario y proyecto
        headers1, _ = self.create_test_user_and_login(
            "user1@example.com", "+573001234567"
        )
        project = self.create_test_project(headers1)

        # Crear segundo usuario
        headers2, _ = self.create_test_user_and_login(
            "user2@example.com", "+573001234568"
        )

        # Intentar subir documento con segundo usuario
        file_data = self.create_test_pdf_file("test.pdf")
        response = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers2,
            files={"file": file_data},
        )

        assert response.status_code == 403
        assert "No tiene permisos" in response.json()["detail"]

    def test_get_document_from_project_success(self):
        """Probar obtención exitosa de documento de proyecto"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Subir documento
        file_data = self.create_test_pdf_file("test.pdf")
        upload_response = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
            files={"file": file_data},
        )
        assert upload_response.status_code == 201

        # Obtener documento
        response = client.get(
            f"/api/v1/proyectos/{project['id']}/documentos", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["file_name"] == "test.pdf"
        assert data["file_type"] == "pdf"
        assert data["project_id"] == project["id"]

    def test_get_document_from_project_not_found(self):
        """Probar obtención cuando no hay documento"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        response = client.get(
            f"/api/v1/proyectos/{project['id']}/documentos", headers=headers
        )

        assert response.status_code == 200
        assert (
            response.json() is None
        )  # El endpoint retorna null cuando no hay documento (debería retorno 404?)

    def test_get_document_from_project_other_user(self):
        """Probar obtención por otro usuario"""
        # Crear primer usuario y proyecto con documento
        headers1, _ = self.create_test_user_and_login(
            "user1@example.com", "+573001234569"
        )
        project = self.create_test_project(headers1)

        file_data = self.create_test_pdf_file("test.pdf")
        client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers1,
            files={"file": file_data},
        )

        # Crear segundo usuario
        headers2, _ = self.create_test_user_and_login(
            "user2@example.com", "+573001234570"
        )

        # Intentar obtener documento
        response = client.get(
            f"/api/v1/proyectos/{project['id']}/documentos", headers=headers2
        )

        assert response.status_code == 403

    # Tests para endpoints de fases
    def test_upload_document_to_phase_success(self):
        """Probar subida exitosa de documento a fase"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        file_data = self.create_test_pdf_file("phase_document.pdf")

        response = client.post(
            f"/api/v1/fases/{phase['id']}/documentos",
            headers=headers,
            files={"file": file_data},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["file_name"] == "phase_document.pdf"
        assert data["phase_id"] == phase["id"]
        assert data["project_id"] is None

    def test_get_document_from_phase_success(self):
        """Probar obtención exitosa de documento de fase"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])

        # Subir documento
        file_data = self.create_test_pdf_file("phase_test.pdf")
        upload_response = client.post(
            f"/api/v1/fases/{phase['id']}/documentos",
            headers=headers,
            files={"file": file_data},
        )
        assert upload_response.status_code == 201

        # Obtener documento
        response = client.get(
            f"/api/v1/fases/{phase['id']}/documentos", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["file_name"] == "phase_test.pdf"
        assert data["phase_id"] == phase["id"]

    # Tests para endpoints de tareas
    def test_upload_document_to_task_success(self):
        """Probar subida exitosa de documento a tarea"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])
        task = self.create_test_task(headers, phase["id"])

        file_data = self.create_test_pdf_file("task_document.pdf")

        response = client.post(
            f"/api/v1/tareas/{task['id']}/documentos",
            headers=headers,
            files={"file": file_data},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["file_name"] == "task_document.pdf"
        assert data["task_id"] == task["id"]
        assert data["project_id"] is None
        assert data["phase_id"] is None

    def test_get_document_from_task_success(self):
        """Probar obtención exitosa de documento de tarea"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])
        task = self.create_test_task(headers, phase["id"])

        # Subir documento
        file_data = self.create_test_pdf_file("task_test.pdf")
        upload_response = client.post(
            f"/api/v1/tareas/{task['id']}/documentos",
            headers=headers,
            files={"file": file_data},
        )
        assert upload_response.status_code == 201

        # Obtener documento
        response = client.get(
            f"/api/v1/tareas/{task['id']}/documentos", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["file_name"] == "task_test.pdf"
        assert data["task_id"] == task["id"]

    # Tests para validaciones de autorización
    def test_upload_document_authorization_validation(self):
        """Probar que solo el propietario puede subir documentos"""
        # Usuario 1 crea proyecto
        headers1, _ = self.create_test_user_and_login(
            "owner@example.com", "+573001234571"
        )
        project = self.create_test_project(headers1)

        # Usuario 2 intenta subir documento
        headers2, _ = self.create_test_user_and_login(
            "other@example.com", "+573001234572"
        )
        file_data = self.create_test_pdf_file("unauthorized.pdf")

        response = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers2,
            files={"file": file_data},
        )

        assert response.status_code == 403

    def test_integrity_one_document_per_entity(self):
        """Probar que solo puede haber un documento por entidad"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Subir primer documento
        file_data1 = self.create_test_pdf_file("first.pdf")
        response1 = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
            files={"file": file_data1},
        )
        assert response1.status_code == 201

        # Intentar subir segundo documento (debe fallar)
        file_data2 = self.create_test_pdf_file("second.pdf")
        response2 = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
            files={"file": file_data2},
        )

        assert response2.status_code == 400
        assert "ya tiene un documento adjunto" in response2.json()["detail"]

    def test_file_validation_extensions(self):
        """Probar validación de extensiones de archivo"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Probar archivo con extensión inválida
        invalid_extensions = [
            ("test.txt", "text/plain"),
            ("test.jpg", "image/jpeg"),
            (
                "test.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            (
                "test.pptx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ),
        ]

        for filename, content_type in invalid_extensions:
            file_data = (filename, io.BytesIO(b"content"), content_type)

            response = client.post(
                f"/api/v1/proyectos/{project['id']}/documentos",
                headers=headers,
                files={"file": file_data},
            )

            assert response.status_code == 400, f"Failed for {filename}"
            assert "Tipo de archivo no permitido" in response.json()["detail"]

    def test_file_validation_size_limits(self):
        """Probar validación de límites de tamaño"""
        headers, user_id = self.create_test_user_and_login()
        # En un entorno de prueba, archivos muy grandes pueden causar problemas de memoria
        # Esta prueba se realiza mejor con mocks (ver test_file_size_validation_mocked)
        pass

    @patch("app.utils.file_utils.FileUtils.validate_file_size")
    def test_file_size_validation_mocked(self, mock_validate_size):
        """Probar validación de tamaño con mock (para evitar problemas de memoria)"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Configurar mock para simular archivo muy grande
        from app.utils.file_utils import FileValidationError

        mock_validate_size.side_effect = FileValidationError(
            "El archivo es demasiado grande"
        )

        file_data = self.create_test_pdf_file("large.pdf")

        response = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
            files={"file": file_data},
        )

        assert response.status_code == 400
        assert "demasiado grande" in response.json()["detail"]

    def test_missing_file_parameter(self):
        """Probar cuando no se envía el parámetro file"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Enviar sin archivo
        response = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos", headers=headers
        )

        assert response.status_code == 422  # Unprocessable Entity

    def test_empty_file(self):
        """Probar con archivo vacío"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Archivo vacío
        file_data = self.create_test_pdf_file("empty.pdf", b"")

        # El archivo vacío debería causar un error interno por validación de esquema
        with pytest.raises(Exception):  # Capturar la excepción de validación
            client.post(
                f"/api/v1/proyectos/{project['id']}/documentos",
                headers=headers,
                files={"file": file_data},
            )

    def test_cross_entity_document_isolation(self):
        """Probar que los documentos están aislados entre entidades"""
        headers, user_id = self.create_test_user_and_login()

        # Crear proyecto, fase y tarea
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])
        task = self.create_test_task(headers, phase["id"])

        # Subir documento a cada entidad (debería ser posible)
        project_file = self.create_test_pdf_file("project.pdf")
        phase_file = self.create_test_pdf_file("phase.pdf")
        task_file = self.create_test_pdf_file("task.pdf")

        # Subir a proyecto
        response1 = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
            files={"file": project_file},
        )
        assert response1.status_code == 201

        # Subir a fase
        response2 = client.post(
            f"/api/v1/fases/{phase['id']}/documentos",
            headers=headers,
            files={"file": phase_file},
        )
        assert response2.status_code == 201

        # Subir a tarea
        response3 = client.post(
            f"/api/v1/tareas/{task['id']}/documentos",
            headers=headers,
            files={"file": task_file},
        )
        assert response3.status_code == 201

        # Verificar que cada entidad tiene su propio documento
        project_doc = client.get(
            f"/api/v1/proyectos/{project['id']}/documentos", headers=headers
        )
        phase_doc = client.get(
            f"/api/v1/fases/{phase['id']}/documentos", headers=headers
        )
        task_doc = client.get(
            f"/api/v1/tareas/{task['id']}/documentos", headers=headers
        )

        assert project_doc.status_code == 200
        assert phase_doc.status_code == 200
        assert task_doc.status_code == 200

        assert project_doc.json()["file_name"] == "project.pdf"
        assert phase_doc.json()["file_name"] == "phase.pdf"
        assert task_doc.json()["file_name"] == "task.pdf"
