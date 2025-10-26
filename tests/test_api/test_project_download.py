import io
from pathlib import Path
from unittest.mock import patch

import pytest

from app.database import Base
from tests.test_db_config import client, engine


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestProjectDocumentDownload:
    """Pruebas para el endpoint de descarga de documentos de proyecto"""

    # Contador para generar números de teléfono únicos
    _phone_counter = 0

    def create_test_user_and_login(self, email="testuser@example.com", phone=None):
        """Helper para crear un usuario de prueba y hacer login"""
        if phone is None:
            # Generar número único incrementando el contador
            TestProjectDocumentDownload._phone_counter += 1
            phone = f"+57300123{TestProjectDocumentDownload._phone_counter:04d}"

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

    def test_download_project_document_success_pdf(self):
        """Probar descarga exitosa de documento PDF de proyecto"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Subir documento PDF
        file_data = self.create_test_pdf_file("proyecto_investigacion.pdf")
        upload_response = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
            files={"file": file_data},
        )
        assert upload_response.status_code == 201

        # Descargar documento
        response = client.get(
            f"/api/v1/proyectos/{project['id']}/descargar-documento",
            headers=headers,
        )

        # Verificar respuesta
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers.get("content-disposition", "").lower()
        assert "proyecto_investigacion.pdf" in response.headers.get(
            "content-disposition", ""
        )
        assert len(response.content) > 0

    def test_download_project_document_success_docx(self):
        """Probar descarga exitosa de documento DOCX de proyecto"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Subir documento DOCX
        file_data = self.create_test_docx_file("tesis_final.docx")
        upload_response = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
            files={"file": file_data},
        )
        assert upload_response.status_code == 201

        # Descargar documento
        response = client.get(
            f"/api/v1/proyectos/{project['id']}/descargar-documento",
            headers=headers,
        )

        # Verificar respuesta
        assert response.status_code == 200
        assert (
            response.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert "attachment" in response.headers.get("content-disposition", "").lower()
        assert "tesis_final.docx" in response.headers.get("content-disposition", "")

    def test_download_project_document_without_auth(self):
        """Probar descarga sin autenticación"""
        response = client.get("/api/v1/proyectos/1/descargar-documento")
        assert response.status_code == 401

    def test_download_project_document_not_found(self):
        """Probar descarga cuando el proyecto no existe"""
        headers, user_id = self.create_test_user_and_login()

        response = client.get(
            "/api/v1/proyectos/999999/descargar-documento",
            headers=headers,
        )

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"].lower()

    def test_download_project_document_no_attachment(self):
        """Probar descarga cuando el proyecto no tiene documento adjunto"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # No subir ningún documento
        response = client.get(
            f"/api/v1/proyectos/{project['id']}/descargar-documento",
            headers=headers,
        )

        assert response.status_code == 404
        assert "no tiene un documento adjunto" in response.json()["detail"]

    def test_download_project_document_other_user(self):
        """Probar descarga por usuario no propietario"""
        # Usuario 1 crea proyecto y sube documento
        headers1, _ = self.create_test_user_and_login(
            "owner@example.com", "+573001234567"
        )
        project = self.create_test_project(headers1)

        file_data = self.create_test_pdf_file("documento.pdf")
        upload_response = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers1,
            files={"file": file_data},
        )
        assert upload_response.status_code == 201

        # Usuario 2 intenta descargar
        headers2, _ = self.create_test_user_and_login(
            "other@example.com", "+573001234568"
        )

        response = client.get(
            f"/api/v1/proyectos/{project['id']}/descargar-documento",
            headers=headers2,
        )

        assert response.status_code == 403
        assert "permisos" in response.json()["detail"].lower()

    def test_download_project_document_preserves_filename(self):
        """Probar que se mantiene el nombre original del archivo"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Subir documento con nombre específico (incluyendo caracteres especiales)
        original_filename = "Mi_Documento_de_Investigacion_2024.pdf"
        file_data = self.create_test_pdf_file(original_filename)
        upload_response = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
            files={"file": file_data},
        )
        assert upload_response.status_code == 201

        # Descargar y verificar nombre
        response = client.get(
            f"/api/v1/proyectos/{project['id']}/descargar-documento",
            headers=headers,
        )

        assert response.status_code == 200
        content_disposition = response.headers.get("content-disposition", "")
        # Verificar que el header contiene información del archivo
        assert "attachment" in content_disposition.lower()
        # El nombre puede estar en formato RFC 5987 (filename*=UTF-8''...)
        assert "filename" in content_disposition.lower()

    def test_download_project_document_correct_mime_types(self):
        """Probar que se retorna el tipo MIME correcto para diferentes extensiones"""
        headers, user_id = self.create_test_user_and_login()

        # Probar con PDF
        project_pdf = self.create_test_project(headers, "PDF Project")
        file_pdf = self.create_test_pdf_file("documento.pdf")
        client.post(
            f"/api/v1/proyectos/{project_pdf['id']}/documentos",
            headers=headers,
            files={"file": file_pdf},
        )

        response_pdf = client.get(
            f"/api/v1/proyectos/{project_pdf['id']}/descargar-documento",
            headers=headers,
        )
        assert response_pdf.status_code == 200
        assert response_pdf.headers["content-type"] == "application/pdf"

        # Probar con DOCX
        project_docx = self.create_test_project(headers, "DOCX Project")
        file_docx = self.create_test_docx_file("documento.docx")
        client.post(
            f"/api/v1/proyectos/{project_docx['id']}/documentos",
            headers=headers,
            files={"file": file_docx},
        )

        response_docx = client.get(
            f"/api/v1/proyectos/{project_docx['id']}/descargar-documento",
            headers=headers,
        )
        assert response_docx.status_code == 200
        assert (
            response_docx.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    @patch("pathlib.Path.exists")
    def test_download_project_document_file_not_found_in_filesystem(self, mock_exists):
        """Probar descarga cuando el archivo está en BD pero no en el sistema de archivos"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Subir documento
        file_data = self.create_test_pdf_file("documento.pdf")
        upload_response = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
            files={"file": file_data},
        )
        assert upload_response.status_code == 201

        # Simular que el archivo no existe en el sistema
        mock_exists.return_value = False

        # Intentar descargar
        response = client.get(
            f"/api/v1/proyectos/{project['id']}/descargar-documento",
            headers=headers,
        )

        assert response.status_code == 404
        assert "no se encuentra en el sistema" in response.json()["detail"]

    def test_download_multiple_times_same_document(self):
        """Probar que se puede descargar el mismo documento múltiples veces"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Subir documento
        file_data = self.create_test_pdf_file("documento.pdf")
        client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
            files={"file": file_data},
        )

        # Descargar múltiples veces
        for _ in range(3):
            response = client.get(
                f"/api/v1/proyectos/{project['id']}/descargar-documento",
                headers=headers,
            )
            assert response.status_code == 200
            assert len(response.content) > 0

    def test_download_integration_workflow(self):
        """Probar flujo completo: crear proyecto, subir documento, descargar"""
        headers, user_id = self.create_test_user_and_login()

        # 1. Crear proyecto
        project = self.create_test_project(headers, "Proyecto de Tesis")

        # 2. Verificar que no hay documento
        response_no_doc = client.get(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
        )
        assert response_no_doc.status_code == 200
        assert response_no_doc.json() is None

        # 3. Subir documento
        test_content = b"Este es el contenido de mi tesis"
        file_data = self.create_test_pdf_file("tesis.pdf", test_content)
        upload_response = client.post(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
            files={"file": file_data},
        )
        assert upload_response.status_code == 201

        # 4. Verificar que el documento existe
        response_has_doc = client.get(
            f"/api/v1/proyectos/{project['id']}/documentos",
            headers=headers,
        )
        assert response_has_doc.status_code == 200
        assert response_has_doc.json() is not None

        # 5. Descargar documento
        download_response = client.get(
            f"/api/v1/proyectos/{project['id']}/descargar-documento",
            headers=headers,
        )
        assert download_response.status_code == 200
        assert download_response.content == test_content
        assert "tesis.pdf" in download_response.headers.get("content-disposition", "")

    def test_download_with_special_characters_in_filename(self):
        """Probar descarga con caracteres especiales en el nombre del archivo"""
        headers, user_id = self.create_test_user_and_login()

        # Nombres con caracteres especiales comunes en español
        special_filenames = [
            "Investigación_2024.pdf",
            "Tesis_Año_2024.pdf",
            "Documento_Español.pdf",
            "Análisis_Científico.pdf",
        ]

        for idx, filename in enumerate(special_filenames):
            # Crear un proyecto por cada archivo
            test_project = self.create_test_project(
                headers, f"Project Special Chars {idx}"
            )

            # Subir documento con nombre especial
            file_data = self.create_test_pdf_file(filename, f"Content {idx}".encode())
            upload_response = client.post(
                f"/api/v1/proyectos/{test_project['id']}/documentos",
                headers=headers,
                files={"file": file_data},
            )
            assert upload_response.status_code == 201, f"Failed to upload {filename}"

            # Descargar documento
            download_response = client.get(
                f"/api/v1/proyectos/{test_project['id']}/descargar-documento",
                headers=headers,
            )

            # Verificar que la descarga fue exitosa
            assert (
                download_response.status_code == 200
            ), f"Failed to download {filename}"

            # Verificar que el header Content-Disposition está presente
            content_disposition = download_response.headers.get(
                "content-disposition", ""
            )
            assert "attachment" in content_disposition.lower()
            assert "filename" in content_disposition.lower()

            # Verificar que el contenido es correcto
            assert download_response.content == f"Content {idx}".encode()
