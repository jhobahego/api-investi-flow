import uuid
from pathlib import Path
from typing import Optional, Tuple

from fastapi import UploadFile

from app.models.attachment import FileType


class FileValidationError(Exception):
    """Error de validación de archivos"""

    pass


class FileUtils:
    """Utilidades para gestión de archivos"""

    # Configuración
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB en bytes
    ALLOWED_MIME_TYPES = {
        FileType.PDF: ["application/pdf"],
        FileType.DOCX: [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ],
    }
    ALLOWED_EXTENSIONS = {FileType.PDF: [".pdf"], FileType.DOCX: [".docx", ".doc"]}

    @staticmethod
    def generate_unique_filename(original_filename: str) -> str:
        """
        Generar un nombre único para el archivo manteniendo la extensión original

        Args:
            original_filename: Nombre original del archivo

        Returns:
            str: Nombre único del archivo
        """
        # Obtener la extensión del archivo
        file_extension = Path(original_filename).suffix.lower()

        # Generar un UUID único
        unique_id = str(uuid.uuid4())

        # Retornar el nombre único con la extensión original
        return f"{unique_id}{file_extension}"

    @staticmethod
    def validate_file_type(file: UploadFile) -> FileType:
        """
        Validar el tipo de archivo basado en MIME type y extensión

        Args:
            file: Archivo subido

        Returns:
            FileType: Tipo de archivo validado

        Raises:
            FileValidationError: Si el tipo de archivo no es válido
        """
        # Validar extensión
        if not file.filename:
            raise FileValidationError("El archivo debe tener un nombre")

        file_extension = Path(file.filename).suffix.lower()

        # Determinar tipo de archivo por extensión
        file_type = None
        for ftype, extensions in FileUtils.ALLOWED_EXTENSIONS.items():
            if file_extension in extensions:
                file_type = ftype
                break

        if not file_type:
            allowed_ext = []
            for exts in FileUtils.ALLOWED_EXTENSIONS.values():
                allowed_ext.extend(exts)
            raise FileValidationError(
                f"Tipo de archivo no permitido. Extensiones permitidas: {', '.join(allowed_ext)}"
            )

        # Validar MIME type si está disponible
        if file.content_type:
            allowed_mimes = FileUtils.ALLOWED_MIME_TYPES[file_type]
            if file.content_type not in allowed_mimes:
                raise FileValidationError(
                    f"Tipo MIME no válido: {file.content_type}. Tipos permitidos: {', '.join(allowed_mimes)}"
                )

        return file_type

    @staticmethod
    def validate_file_size(file_size: int) -> None:
        """
        Validar el tamaño del archivo

        Args:
            file_size: Tamaño del archivo en bytes

        Raises:
            FileValidationError: Si el archivo es demasiado grande
        """
        if file_size > FileUtils.MAX_FILE_SIZE:
            max_size_mb = FileUtils.MAX_FILE_SIZE / (1024 * 1024)
            raise FileValidationError(
                f"El archivo es demasiado grande. Tamaño máximo: {max_size_mb}MB"
            )

    @staticmethod
    def create_directory_structure(
        base_path: str, parent_type: str, parent_id: int
    ) -> str:
        """
        Crear la estructura de directorios para almacenar el archivo

        Args:
            base_path: Ruta base (ej: 'uploads/documents')
            parent_type: Tipo de padre ('projects', 'phases', 'tasks')
            parent_id: ID del padre

        Returns:
            str: Ruta completa del directorio creado
        """
        # Crear la ruta del directorio
        directory_path = Path(base_path) / parent_type / str(parent_id)

        # Crear los directorios si no existen
        directory_path.mkdir(parents=True, exist_ok=True)

        return str(directory_path)

    @staticmethod
    def build_file_path(parent_type: str, parent_id: int, filename: str) -> str:
        """
        Construir la ruta completa del archivo

        Args:
            parent_type: Tipo de padre ('projects', 'phases', 'tasks')
            parent_id: ID del padre
            filename: Nombre del archivo

        Returns:
            str: Ruta completa del archivo
        """
        base_path = "uploads/documents"
        directory = FileUtils.create_directory_structure(
            base_path, parent_type, parent_id
        )
        return str(Path(directory) / filename)

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """
        Eliminar un archivo del sistema de archivos

        Args:
            file_path: Ruta del archivo a eliminar

        Returns:
            bool: True si se eliminó correctamente, False si no existía
        """
        try:
            file_path_obj = Path(file_path)
            if file_path_obj.exists():
                file_path_obj.unlink()

                # Intentar eliminar el directorio padre si está vacío
                try:
                    file_path_obj.parent.rmdir()
                except OSError:
                    # El directorio no está vacío, no hacer nada
                    pass

                return True
            return False
        except Exception:
            # Error al eliminar el archivo
            return False

    @staticmethod
    def get_file_info(file: UploadFile) -> Tuple[str, int, Optional[str]]:
        """
        Obtener información del archivo

        Args:
            file: Archivo subido

        Returns:
            Tuple[str, int, Optional[str]]: (nombre, tamaño, tipo MIME)
        """
        # Obtener tamaño del archivo
        file.file.seek(0, 2)  # Ir al final del archivo
        file_size = file.file.tell()
        file.file.seek(0)  # Volver al principio

        return file.filename or "unknown", file_size, file.content_type

    @staticmethod
    def ensure_upload_directory() -> None:
        """
        Asegurar que el directorio de uploads existe
        """
        upload_dir = Path("uploads/documents")
        upload_dir.mkdir(parents=True, exist_ok=True)
