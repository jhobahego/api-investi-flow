import io
import os
import tempfile
from typing import Optional
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.attachment import Attachment, FileType
from app.schemas.attachment import AttachmentUpdate
from app.services.attachment_service import AttachmentService
from app.utils.file_utils import FileValidationError


class TestAttachmentService:
    """Pruebas para el servicio de adjuntos"""

    def setup_method(self):
        """Configurar cada prueba"""
        self.service = AttachmentService()
        self.mock_db = Mock(spec=Session)

    def create_mock_upload_file(
        self,
        filename="test.pdf",
        content=b"test content",
        content_type="application/pdf",
    ):
        """Helper para crear mock de UploadFile"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = filename
        mock_file.content_type = content_type
        mock_file.file = io.BytesIO(content)
        return mock_file

    def create_mock_attachment(
        self,
        attachment_id: int = 1,
        project_id: Optional[int] = 1,
        phase_id: Optional[int] = None,
        task_id: Optional[int] = None,
    ):
        """Helper para crear mock de Attachment"""
        attachment = Mock(spec=Attachment)
        attachment.id = attachment_id
        attachment.project_id = project_id
        attachment.phase_id = phase_id
        attachment.task_id = task_id
        attachment.file_name = "test.pdf"
        attachment.file_path = "/uploads/documents/projects/1/test.pdf"
        attachment.file_type = FileType.PDF
        attachment.file_size = 1024
        return attachment

    def create_mock_project(self, project_id=1, owner_id=1):
        """Helper para crear mock de Project"""
        project = Mock()
        project.id = project_id
        project.owner_id = owner_id
        return project

    def create_mock_phase(self, phase_id=1, project_id=1):
        """Helper para crear mock de Phase"""
        phase = Mock()
        phase.id = phase_id
        phase.project_id = project_id
        return phase

    def create_mock_task(self, task_id=1, phase_id=1):
        """Helper para crear mock de Task"""
        task = Mock()
        task.id = task_id
        task.phase_id = phase_id
        return task

    @patch("app.services.attachment_service.FileUtils.get_file_info")
    @patch("app.services.attachment_service.FileUtils.validate_file_type")
    @patch("app.services.attachment_service.FileUtils.validate_file_size")
    @patch("app.services.attachment_service.FileUtils.generate_unique_filename")
    @patch("app.services.attachment_service.FileUtils.build_file_path")
    @patch("app.services.attachment_service.FileUtils.ensure_upload_directory")
    def test_create_attachment_project_success(
        self,
        mock_ensure_dir,
        mock_build_path,
        mock_unique_name,
        mock_validate_size,
        mock_validate_type,
        mock_file_info,
    ):
        """Probar creación exitosa de adjunto en proyecto"""
        # Configurar mocks
        mock_file = self.create_mock_upload_file()
        mock_project = self.create_mock_project()

        # Configurar repositorios
        self.service.project_repository.get = Mock(return_value=mock_project)
        self.service.attachment_repository.has_attachment = Mock(return_value=False)
        self.service.attachment_repository.create_attachment = Mock(
            return_value=self.create_mock_attachment()
        )

        # Configurar file utils
        mock_file_info.return_value = ("test.pdf", 1024, "application/pdf")
        mock_validate_type.return_value = FileType.PDF
        mock_unique_name.return_value = "unique-test.pdf"
        mock_build_path.return_value = "/uploads/documents/projects/1/unique-test.pdf"

        # Mock para _save_file
        self.service._save_file = Mock()

        # Ejecutar
        result = self.service.create_attachment(
            self.mock_db, mock_file, "project", 1, 1
        )

        # Verificar
        assert result is not None
        self.service.project_repository.get.assert_called_once_with(self.mock_db, 1)
        self.service.attachment_repository.has_attachment.assert_called_once_with(
            self.mock_db, 1, "project"
        )
        mock_validate_type.assert_called_once_with(mock_file)
        mock_validate_size.assert_called_once_with(1024)
        self.service._save_file.assert_called_once()
        self.mock_db.commit.assert_called_once()

    def test_create_attachment_project_not_found(self):
        """Probar creación de adjunto cuando proyecto no existe"""
        mock_file = self.create_mock_upload_file()

        # Proyecto no existe
        self.service.project_repository.get = Mock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            self.service.create_attachment(self.mock_db, mock_file, "project", 999, 1)

        assert exc_info.value.status_code == 404
        assert "Proyecto no encontrado" in str(exc_info.value.detail)

    def test_create_attachment_project_permission_denied(self):
        """Probar creación de adjunto sin permisos en proyecto"""
        mock_file = self.create_mock_upload_file()
        mock_project = self.create_mock_project(
            project_id=1, owner_id=2
        )  # Otro usuario

        self.service.project_repository.get = Mock(return_value=mock_project)

        with pytest.raises(HTTPException) as exc_info:
            self.service.create_attachment(
                self.mock_db,
                mock_file,
                "project",
                1,
                1,  # user_id=1, pero owner_id=2
            )

        assert exc_info.value.status_code == 403
        assert "No tiene permisos" in str(exc_info.value.detail)

    def test_create_attachment_already_exists(self):
        """Probar creación cuando ya existe un adjunto"""
        mock_file = self.create_mock_upload_file()
        mock_project = self.create_mock_project()

        self.service.project_repository.get = Mock(return_value=mock_project)
        self.service.attachment_repository.has_attachment = Mock(return_value=True)

        with pytest.raises(HTTPException) as exc_info:
            self.service.create_attachment(self.mock_db, mock_file, "project", 1, 1)

        assert exc_info.value.status_code == 400
        assert "ya tiene un documento adjunto" in str(exc_info.value.detail)

    @patch("app.services.attachment_service.FileUtils.validate_file_type")
    def test_create_attachment_invalid_file_type(self, mock_validate_type):
        """Probar creación con tipo de archivo inválido"""
        mock_file = self.create_mock_upload_file()
        mock_project = self.create_mock_project()

        self.service.project_repository.get = Mock(return_value=mock_project)
        self.service.attachment_repository.has_attachment = Mock(return_value=False)
        mock_validate_type.side_effect = FileValidationError("Tipo no permitido")

        with pytest.raises(HTTPException) as exc_info:
            self.service.create_attachment(self.mock_db, mock_file, "project", 1, 1)

        assert exc_info.value.status_code == 400
        assert "Tipo no permitido" in str(exc_info.value.detail)

    @patch("app.services.attachment_service.FileUtils.get_file_info")
    @patch("app.services.attachment_service.FileUtils.validate_file_size")
    def test_create_attachment_file_too_large(self, mock_validate_size, mock_file_info):
        """Probar creación con archivo muy grande"""
        mock_file = self.create_mock_upload_file()
        mock_project = self.create_mock_project()

        self.service.project_repository.get = Mock(return_value=mock_project)
        self.service.attachment_repository.has_attachment = Mock(return_value=False)
        mock_file_info.return_value = (
            "test.pdf",
            60 * 1024 * 1024,
            "application/pdf",
        )  # 60MB
        mock_validate_size.side_effect = FileValidationError("Archivo muy grande")

        with pytest.raises(HTTPException) as exc_info:
            self.service.create_attachment(self.mock_db, mock_file, "project", 1, 1)

        assert exc_info.value.status_code == 400
        assert "Archivo muy grande" in str(exc_info.value.detail)

    def test_create_attachment_phase_success(self):
        """Probar creación exitosa de adjunto en fase"""
        mock_file = self.create_mock_upload_file()
        mock_phase = self.create_mock_phase(phase_id=1, project_id=1)
        mock_project = self.create_mock_project(project_id=1, owner_id=1)

        # Configurar mocks
        self.service.phase_repository.get = Mock(return_value=mock_phase)
        self.service.project_repository.get = Mock(return_value=mock_project)
        self.service.attachment_repository.has_attachment = Mock(return_value=False)

        # Mock todos los métodos necesarios
        with patch.multiple(
            "app.services.attachment_service.FileUtils",
            get_file_info=Mock(return_value=("test.pdf", 1024, "application/pdf")),
            validate_file_type=Mock(return_value=FileType.PDF),
            validate_file_size=Mock(),
            generate_unique_filename=Mock(return_value="unique-test.pdf"),
            build_file_path=Mock(return_value="/path/to/file"),
            ensure_upload_directory=Mock(),
        ):
            self.service._save_file = Mock()
            self.service.attachment_repository.create_attachment = Mock(
                return_value=self.create_mock_attachment(phase_id=1, project_id=None)
            )

            result = self.service.create_attachment(
                self.mock_db, mock_file, "phase", 1, 1
            )

            assert result is not None
            self.service.phase_repository.get.assert_called_once_with(self.mock_db, 1)
            self.service.project_repository.get.assert_called_once_with(self.mock_db, 1)

    def test_create_attachment_task_success(self):
        """Probar creación exitosa de adjunto en tarea"""
        mock_file = self.create_mock_upload_file()
        mock_task = self.create_mock_task(task_id=1, phase_id=1)
        mock_phase = self.create_mock_phase(phase_id=1, project_id=1)
        mock_project = self.create_mock_project(project_id=1, owner_id=1)

        # Configurar mocks
        self.service.task_repository.get = Mock(return_value=mock_task)
        self.service.phase_repository.get = Mock(return_value=mock_phase)
        self.service.project_repository.get = Mock(return_value=mock_project)
        self.service.attachment_repository.has_attachment = Mock(return_value=False)

        # Mock todos los métodos necesarios
        with patch.multiple(
            "app.services.attachment_service.FileUtils",
            get_file_info=Mock(return_value=("test.pdf", 1024, "application/pdf")),
            validate_file_type=Mock(return_value=FileType.PDF),
            validate_file_size=Mock(),
            generate_unique_filename=Mock(return_value="unique-test.pdf"),
            build_file_path=Mock(return_value="/path/to/file"),
            ensure_upload_directory=Mock(),
        ):
            self.service._save_file = Mock()
            self.service.attachment_repository.create_attachment = Mock(
                return_value=self.create_mock_attachment(
                    task_id=1, project_id=None, phase_id=None
                )
            )

            result = self.service.create_attachment(
                self.mock_db, mock_file, "task", 1, 1
            )

            assert result is not None
            self.service.task_repository.get.assert_called_once_with(self.mock_db, 1)

    def test_create_attachment_invalid_parent_type(self):
        """Probar creación con tipo de padre inválido"""
        mock_file = self.create_mock_upload_file()

        with pytest.raises(HTTPException) as exc_info:
            self.service.create_attachment(
                self.mock_db, mock_file, "invalid_type", 1, 1
            )

        assert exc_info.value.status_code == 400
        assert "Tipo de entidad padre no válido" in str(exc_info.value.detail)

    def test_get_attachment_by_parent_project_success(self):
        """Probar obtención exitosa de adjunto por proyecto"""
        mock_project = self.create_mock_project()
        mock_attachment = self.create_mock_attachment()

        self.service.project_repository.get = Mock(return_value=mock_project)
        self.service.attachment_repository.get_attachment_by_parent = Mock(
            return_value=mock_attachment
        )

        result = self.service.get_attachment_by_parent(self.mock_db, "project", 1, 1)

        assert result == mock_attachment
        self.service.project_repository.get.assert_called_once_with(self.mock_db, 1)
        self.service.attachment_repository.get_attachment_by_parent.assert_called_once_with(
            self.mock_db, 1, "project"
        )

    def test_get_attachment_by_parent_not_found(self):
        """Probar obtención cuando no existe adjunto"""
        mock_project = self.create_mock_project()

        self.service.project_repository.get = Mock(return_value=mock_project)
        self.service.attachment_repository.get_attachment_by_parent = Mock(
            return_value=None
        )

        result = self.service.get_attachment_by_parent(self.mock_db, "project", 1, 1)

        assert result is None

    def test_get_attachment_by_parent_permission_denied(self):
        """Probar obtención sin permisos"""
        mock_project = self.create_mock_project(
            project_id=1, owner_id=2
        )  # Otro usuario

        self.service.project_repository.get = Mock(return_value=mock_project)

        with pytest.raises(HTTPException) as exc_info:
            self.service.get_attachment_by_parent(
                self.mock_db,
                "project",
                1,
                1,  # user_id=1, pero owner_id=2
            )

        assert exc_info.value.status_code == 403

    def test_update_attachment_success(self):
        """Probar actualización exitosa de adjunto"""
        mock_attachment = self.create_mock_attachment()
        mock_project = self.create_mock_project()
        update_data = AttachmentUpdate(file_name="updated_name.pdf")

        self.service.attachment_repository.get = Mock(return_value=mock_attachment)
        self.service.project_repository.get = Mock(return_value=mock_project)
        self.service.attachment_repository.update_attachment = Mock(
            return_value=mock_attachment
        )

        result = self.service.update_attachment(self.mock_db, 1, update_data, 1)

        assert result == mock_attachment
        self.service.attachment_repository.update_attachment.assert_called_once_with(
            self.mock_db, 1, update_data
        )
        self.mock_db.commit.assert_called_once()

    def test_update_attachment_not_found(self):
        """Probar actualización de adjunto que no existe"""
        update_data = AttachmentUpdate(file_name="updated_name.pdf")

        self.service.attachment_repository.get = Mock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            self.service.update_attachment(self.mock_db, 999, update_data, 1)

        assert exc_info.value.status_code == 404
        assert "Adjunto no encontrado" in str(exc_info.value.detail)

    @patch("app.services.attachment_service.FileUtils.delete_file")
    def test_delete_attachment_success(self, mock_delete_file):
        """Probar eliminación exitosa de adjunto"""
        mock_attachment = self.create_mock_attachment()
        mock_project = self.create_mock_project()

        self.service.attachment_repository.get = Mock(return_value=mock_attachment)
        self.service.project_repository.get = Mock(return_value=mock_project)
        self.service.attachment_repository.remove = Mock(return_value=True)

        result = self.service.delete_attachment(self.mock_db, 1, 1)

        assert result is True
        mock_delete_file.assert_called_once_with(str(mock_attachment.file_path))
        self.service.attachment_repository.remove.assert_called_once_with(
            self.mock_db, id=1
        )
        self.mock_db.commit.assert_called_once()

    def test_delete_attachment_not_found(self):
        """Probar eliminación de adjunto que no existe"""
        self.service.attachment_repository.get = Mock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            self.service.delete_attachment(self.mock_db, 999, 1)

        assert exc_info.value.status_code == 404
        assert "Adjunto no encontrado" in str(exc_info.value.detail)

    @patch("app.services.attachment_service.FileUtils.delete_file")
    def test_delete_attachment_database_error(self, mock_delete_file):
        """Probar error en base de datos al eliminar adjunto"""
        mock_attachment = self.create_mock_attachment()
        mock_project = self.create_mock_project()

        self.service.attachment_repository.get = Mock(return_value=mock_attachment)
        self.service.project_repository.get = Mock(return_value=mock_project)
        self.service.attachment_repository.remove = Mock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            self.service.delete_attachment(self.mock_db, 1, 1)

        assert exc_info.value.status_code == 500
        assert "Error al eliminar el adjunto" in str(exc_info.value.detail)
        self.mock_db.rollback.assert_called_once()

    def test_replace_attachment_success(self):
        """Probar reemplazo exitoso de adjunto"""
        mock_file = self.create_mock_upload_file()
        mock_project = self.create_mock_project()
        old_attachment = self.create_mock_attachment()
        new_attachment = self.create_mock_attachment(attachment_id=2)

        self.service.project_repository.get = Mock(return_value=mock_project)
        self.service.attachment_repository.get_attachment_by_parent = Mock(
            return_value=old_attachment
        )

        # Mock para create_attachment
        self.service.create_attachment = Mock(return_value=new_attachment)
        self.service.attachment_repository.remove = Mock(return_value=True)

        with patch(
            "app.services.attachment_service.FileUtils.delete_file"
        ) as mock_delete:
            result = self.service.replace_attachment(
                self.mock_db, mock_file, "project", 1, 1
            )

            assert result == new_attachment
            self.service.create_attachment.assert_called_once_with(
                self.mock_db, mock_file, "project", 1, 1
            )
            self.service.attachment_repository.remove.assert_called_once_with(
                self.mock_db, id=old_attachment.id
            )
            mock_delete.assert_called_once_with(str(old_attachment.file_path))

    def test_replace_attachment_no_existing(self):
        """Probar reemplazo cuando no existe adjunto previo"""
        mock_file = self.create_mock_upload_file()
        mock_project = self.create_mock_project()

        self.service.project_repository.get = Mock(return_value=mock_project)
        self.service.attachment_repository.get_attachment_by_parent = Mock(
            return_value=None
        )

        with pytest.raises(HTTPException) as exc_info:
            self.service.replace_attachment(self.mock_db, mock_file, "project", 1, 1)

        assert exc_info.value.status_code == 404
        assert "No existe un documento adjunto" in str(exc_info.value.detail)

    def test_get_parent_info_project(self):
        """Probar obtención de información del padre para proyecto"""
        attachment = self.create_mock_attachment(
            project_id=1, phase_id=None, task_id=None
        )

        parent_type, parent_id = self.service._get_parent_info(attachment)

        assert parent_type == "project"
        assert parent_id == 1

    def test_get_parent_info_phase(self):
        """Probar obtención de información del padre para fase"""
        attachment = self.create_mock_attachment(
            project_id=None, phase_id=2, task_id=None
        )

        parent_type, parent_id = self.service._get_parent_info(attachment)

        assert parent_type == "phase"
        assert parent_id == 2

    def test_get_parent_info_task(self):
        """Probar obtención de información del padre para tarea"""
        attachment = self.create_mock_attachment(
            project_id=None, phase_id=None, task_id=3
        )

        parent_type, parent_id = self.service._get_parent_info(attachment)

        assert parent_type == "task"
        assert parent_id == 3

    def test_get_parent_info_no_parent(self):
        """Probar error cuando adjunto no tiene padre válido"""
        attachment = self.create_mock_attachment(
            project_id=None, phase_id=None, task_id=None
        )

        with pytest.raises(ValueError, match="Adjunto sin entidad padre válida"):
            self.service._get_parent_info(attachment)

    def test_get_parent_type_plural(self):
        """Probar obtención de formas plurales"""
        assert self.service._get_parent_type_plural("project") == "projects"
        assert self.service._get_parent_type_plural("phase") == "phases"
        assert self.service._get_parent_type_plural("task") == "tasks"

        with pytest.raises(ValueError, match="Tipo de padre no válido"):
            self.service._get_parent_type_plural("invalid")

    def test_save_file_success(self):
        """Probar guardado exitoso de archivo"""
        mock_file = self.create_mock_upload_file()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.pdf")

            self.service._save_file(mock_file, file_path)

            # Verificar que el archivo fue creado
            assert os.path.exists(file_path)

            # Verificar contenido
            with open(file_path, "rb") as f:
                content = f.read()
            assert content == b"test content"

    def test_save_file_error(self):
        """Probar error al guardar archivo"""
        mock_file = self.create_mock_upload_file()
        invalid_path = "/invalid/path/that/does/not/exist/test.pdf"

        with pytest.raises(Exception, match="Error al guardar archivo"):
            self.service._save_file(mock_file, invalid_path)

    def test_validate_parent_entity_invalid_type(self):
        """Probar validación con tipo de entidad inválido"""
        with pytest.raises(HTTPException) as exc_info:
            self.service._validate_parent_entity(self.mock_db, "invalid_type", 1, 1)

        assert exc_info.value.status_code == 400
        assert "Tipo de entidad padre no válido" in str(exc_info.value.detail)
