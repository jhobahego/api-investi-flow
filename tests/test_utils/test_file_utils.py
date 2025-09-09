import io
import os
import tempfile
import uuid
from unittest.mock import Mock, patch

import pytest
from fastapi import UploadFile

from app.models.attachment import FileType
from app.utils.file_utils import FileUtils, FileValidationError


class TestFileUtils:
    """Pruebas para las utilidades de gestión de archivos"""

    def test_generate_unique_filename_with_pdf(self):
        """Probar generación de nombre único para PDF"""
        original_filename = "document.pdf"
        unique_filename = FileUtils.generate_unique_filename(original_filename)

        # Verificar que tiene la extensión correcta
        assert unique_filename.endswith(".pdf")

        # Verificar que es diferente al original
        assert unique_filename != original_filename

        # Verificar que contiene un UUID válido
        name_without_ext = unique_filename.replace(".pdf", "")
        uuid.UUID(name_without_ext)  # Esto debería funcionar sin excepción

    def test_generate_unique_filename_with_docx(self):
        """Probar generación de nombre único para DOCX"""
        original_filename = "thesis.docx"
        unique_filename = FileUtils.generate_unique_filename(original_filename)

        assert unique_filename.endswith(".docx")
        assert unique_filename != original_filename

        name_without_ext = unique_filename.replace(".docx", "")
        uuid.UUID(name_without_ext)

    def test_generate_unique_filename_case_insensitive(self):
        """Probar que la extensión se maneja en minúsculas"""
        original_filename = "DOCUMENT.PDF"
        unique_filename = FileUtils.generate_unique_filename(original_filename)

        assert unique_filename.endswith(".pdf")  # Debe convertir a minúsculas

    def test_generate_unique_filename_multiple_calls(self):
        """Probar que múltiples llamadas generan nombres diferentes"""
        original_filename = "test.pdf"

        filenames = [
            FileUtils.generate_unique_filename(original_filename) for _ in range(5)
        ]

        # Todos deben ser únicos
        assert len(set(filenames)) == 5

    def test_validate_file_type_pdf_success(self):
        """Probar validación exitosa de archivo PDF"""
        # Crear mock de UploadFile para PDF
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "document.pdf"
        mock_file.content_type = "application/pdf"

        file_type = FileUtils.validate_file_type(mock_file)
        assert file_type == FileType.PDF

    def test_validate_file_type_docx_success(self):
        """Probar validación exitosa de archivo DOCX"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "document.docx"
        mock_file.content_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        file_type = FileUtils.validate_file_type(mock_file)
        assert file_type == FileType.DOCX

    def test_validate_file_type_doc_success(self):
        """Probar validación exitosa de archivo DOC"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "document.doc"
        mock_file.content_type = "application/msword"

        file_type = FileUtils.validate_file_type(mock_file)
        assert file_type == FileType.DOCX

    def test_validate_file_type_no_filename(self):
        """Probar validación falla sin nombre de archivo"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = None

        with pytest.raises(
            FileValidationError, match="El archivo debe tener un nombre"
        ):
            FileUtils.validate_file_type(mock_file)

    def test_validate_file_type_invalid_extension(self):
        """Probar validación falla con extensión inválida"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "document.txt"
        mock_file.content_type = "text/plain"

        with pytest.raises(FileValidationError, match="Tipo de archivo no permitido"):
            FileUtils.validate_file_type(mock_file)

    def test_validate_file_type_invalid_mime_type(self):
        """Probar validación falla con MIME type inválido"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "document.pdf"
        mock_file.content_type = "text/plain"  # MIME type incorrecto

        with pytest.raises(FileValidationError, match="Tipo MIME no válido"):
            FileUtils.validate_file_type(mock_file)

    def test_validate_file_type_no_content_type(self):
        """Probar validación funciona sin content_type"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "document.pdf"
        mock_file.content_type = None

        # Debe funcionar solo con la extensión
        file_type = FileUtils.validate_file_type(mock_file)
        assert file_type == FileType.PDF

    def test_validate_file_size_valid(self):
        """Probar validación exitosa de tamaño de archivo"""
        # Archivo de 10MB (válido)
        file_size = 10 * 1024 * 1024

        # No debe lanzar excepción
        FileUtils.validate_file_size(file_size)

    def test_validate_file_size_max_allowed(self):
        """Probar validación con tamaño máximo permitido"""
        # Archivo de exactamente 50MB
        file_size = 50 * 1024 * 1024

        # No debe lanzar excepción
        FileUtils.validate_file_size(file_size)

    def test_validate_file_size_too_large(self):
        """Probar validación falla con archivo muy grande"""
        # Archivo de 51MB (demasiado grande)
        file_size = 51 * 1024 * 1024

        with pytest.raises(FileValidationError, match="El archivo es demasiado grande"):
            FileUtils.validate_file_size(file_size)

    def test_validate_file_size_zero(self):
        """Probar validación con archivo de tamaño cero"""
        file_size = 0

        # Debería pasar (archivo vacío válido)
        FileUtils.validate_file_size(file_size)

    def test_create_directory_structure(self):
        """Probar creación de estructura de directorios"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = temp_dir
            parent_type = "projects"
            parent_id = 123

            created_dir = FileUtils.create_directory_structure(
                base_path, parent_type, parent_id
            )

            expected_path = os.path.join(base_path, parent_type, str(parent_id))
            assert created_dir == expected_path
            assert os.path.exists(created_dir)
            assert os.path.isdir(created_dir)

    def test_create_directory_structure_already_exists(self):
        """Probar creación cuando el directorio ya existe"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = temp_dir
            parent_type = "phases"
            parent_id = 456

            # Crear el directorio manualmente primero
            expected_path = os.path.join(base_path, parent_type, str(parent_id))
            os.makedirs(expected_path)

            # Ahora usar la función
            created_dir = FileUtils.create_directory_structure(
                base_path, parent_type, parent_id
            )

            assert created_dir == expected_path
            assert os.path.exists(created_dir)

    def test_build_file_path(self):
        """Probar construcción de ruta de archivo"""
        parent_type = "tasks"
        parent_id = 789
        filename = "test-file.pdf"

        file_path = FileUtils.build_file_path(parent_type, parent_id, filename)

        expected_path = f"uploads/documents/{parent_type}/{parent_id}/{filename}"
        assert file_path == expected_path

    @patch("app.utils.file_utils.FileUtils.create_directory_structure")
    def test_build_file_path_creates_directory(self, mock_create_dir):
        """Probar que build_file_path crea directorios"""
        mock_create_dir.return_value = "/test/path"

        FileUtils.build_file_path("projects", 1, "file.pdf")

        mock_create_dir.assert_called_once_with("uploads/documents", "projects", 1)

    def test_delete_file_success(self):
        """Probar eliminación exitosa de archivo"""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(b"test content")

        # Verificar que el archivo existe
        assert os.path.exists(temp_path)

        # Eliminar el archivo
        result = FileUtils.delete_file(temp_path)

        assert result is True
        assert not os.path.exists(temp_path)

    def test_delete_file_not_exists(self):
        """Probar eliminación de archivo que no existe"""
        non_existent_path = "/path/that/does/not/exist.pdf"

        result = FileUtils.delete_file(non_existent_path)

        assert result is False

    def test_delete_file_removes_empty_parent_directory(self):
        """Probar que se elimina directorio padre vacío"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Crear estructura de directorios
            parent_dir = os.path.join(temp_dir, "test_parent")
            os.makedirs(parent_dir)

            # Crear archivo en el directorio
            file_path = os.path.join(parent_dir, "test_file.pdf")
            with open(file_path, "w") as f:
                f.write("test")

            # Eliminar el archivo
            result = FileUtils.delete_file(file_path)

            assert result is True
            assert not os.path.exists(file_path)
            # El directorio padre debería haberse eliminado también
            assert not os.path.exists(parent_dir)

    def test_delete_file_keeps_non_empty_parent_directory(self):
        """Probar que no se elimina directorio padre con otros archivos"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Crear estructura de directorios
            parent_dir = os.path.join(temp_dir, "test_parent")
            os.makedirs(parent_dir)

            # Crear dos archivos
            file1_path = os.path.join(parent_dir, "file1.pdf")
            file2_path = os.path.join(parent_dir, "file2.pdf")

            with open(file1_path, "w") as f:
                f.write("test1")
            with open(file2_path, "w") as f:
                f.write("test2")

            # Eliminar solo uno
            result = FileUtils.delete_file(file1_path)

            assert result is True
            assert not os.path.exists(file1_path)
            assert os.path.exists(file2_path)
            # El directorio padre debe seguir existiendo
            assert os.path.exists(parent_dir)

    def test_get_file_info_success(self):
        """Probar obtención de información de archivo"""
        # Crear mock de archivo
        file_content = b"test content for file"
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test_document.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.file = io.BytesIO(file_content)

        filename, file_size, content_type = FileUtils.get_file_info(mock_file)

        assert filename == "test_document.pdf"
        assert file_size == len(file_content)
        assert content_type == "application/pdf"

        # Verificar que el puntero del archivo volvió al inicio
        assert mock_file.file.tell() == 0

    def test_get_file_info_no_filename(self):
        """Probar obtención de información sin nombre de archivo"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = None
        mock_file.content_type = "application/pdf"
        mock_file.file = io.BytesIO(b"content")

        filename, file_size, content_type = FileUtils.get_file_info(mock_file)

        assert filename == "unknown"
        assert file_size == 7  # len(b"content")
        assert content_type == "application/pdf"

    def test_get_file_info_large_file(self):
        """Probar obtención de información de archivo grande"""
        # Crear archivo de 1MB
        large_content = b"x" * (1024 * 1024)
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "large_file.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.file = io.BytesIO(large_content)

        filename, file_size, content_type = FileUtils.get_file_info(mock_file)

        assert filename == "large_file.pdf"
        assert file_size == 1024 * 1024
        assert content_type == "application/pdf"

    def test_ensure_upload_directory(self):
        """Probar creación del directorio de uploads"""
        # Usar un directorio temporal para la prueba
        with patch("app.utils.file_utils.Path") as mock_path:
            mock_upload_dir = Mock()
            mock_path.return_value = mock_upload_dir

            FileUtils.ensure_upload_directory()

            mock_path.assert_called_once_with("uploads/documents")
            mock_upload_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_allowed_extensions_configuration(self):
        """Probar configuración de extensiones permitidas"""
        # Verificar que las extensiones están configuradas correctamente
        assert FileType.PDF in FileUtils.ALLOWED_EXTENSIONS
        assert FileType.DOCX in FileUtils.ALLOWED_EXTENSIONS

        pdf_extensions = FileUtils.ALLOWED_EXTENSIONS[FileType.PDF]
        docx_extensions = FileUtils.ALLOWED_EXTENSIONS[FileType.DOCX]

        assert ".pdf" in pdf_extensions
        assert ".docx" in docx_extensions
        assert ".doc" in docx_extensions

    def test_allowed_mime_types_configuration(self):
        """Probar configuración de tipos MIME permitidos"""
        # Verificar que los MIME types están configurados correctamente
        assert FileType.PDF in FileUtils.ALLOWED_MIME_TYPES
        assert FileType.DOCX in FileUtils.ALLOWED_MIME_TYPES

        pdf_mimes = FileUtils.ALLOWED_MIME_TYPES[FileType.PDF]
        docx_mimes = FileUtils.ALLOWED_MIME_TYPES[FileType.DOCX]

        assert "application/pdf" in pdf_mimes
        assert (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            in docx_mimes
        )
        assert "application/msword" in docx_mimes

    def test_max_file_size_configuration(self):
        """Probar configuración de tamaño máximo de archivo"""
        # Verificar que el tamaño máximo es 50MB
        expected_size = 50 * 1024 * 1024  # 50MB en bytes
        assert FileUtils.MAX_FILE_SIZE == expected_size
