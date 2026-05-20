from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.attachment import Attachment
from app.repositories.attachment_repository import AttachmentRepository
from app.repositories.phase_repository import PhaseRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.attachment import AttachmentCreate, AttachmentUpdate
from app.services.base import BaseService
from app.utils.file_utils import FileUtils, FileValidationError


class AttachmentService(BaseService[Attachment, AttachmentCreate, AttachmentUpdate]):
    """Servicio para gestión de adjuntos con validaciones de negocio"""

    def __init__(self):
        self.attachment_repository = AttachmentRepository()
        self.project_repository = ProjectRepository()
        self.phase_repository = PhaseRepository()
        self.task_repository = TaskRepository()
        super().__init__(self.attachment_repository)

    def create_attachment(
        self,
        db: Session,
        file: UploadFile,
        parent_type: str,
        parent_id: int,
        user_id: int,
    ) -> Attachment:
        """
        Crear un nuevo adjunto con validaciones de negocio

        Args:
            db: Sesión de base de datos
            file: Archivo subido
            parent_type: Tipo de padre ('project', 'phase', 'task')
            parent_id: ID del padre
            user_id: ID del usuario que sube el archivo

        Returns:
            Attachment: El adjunto creado

        Raises:
            HTTPException: Si hay errores de validación o permisos
        """
        # Validar que la entidad padre existe y pertenece al propietario
        self._validate_parent_entity(db, parent_type, parent_id, user_id)

        # Validar que no existe un adjunto previo
        if self.attachment_repository.has_attachment(db, parent_id, parent_type):
            raise HTTPException(
                status_code=400,
                detail=f"La {parent_type} ya tiene un documento adjunto.",
            )

        # Obtener información del archivo
        filename, file_size, _ = FileUtils.get_file_info(file)

        # Validar tipo de archivo
        try:
            file_type = FileUtils.validate_file_type(file)
        except FileValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Validar tamaño del archivo
        try:
            FileUtils.validate_file_size(file_size)
        except FileValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Generar nombre único y construir ruta
        unique_filename = FileUtils.generate_unique_filename(filename)
        parent_type_plural = self._get_parent_type_plural(parent_type)
        file_path = FileUtils.build_file_path(
            parent_type_plural, parent_id, unique_filename
        )

        # Asegurar que el directorio existe
        FileUtils.ensure_upload_directory()

        # Guardar el archivo
        try:
            self._save_file(file, file_path)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error al guardar el archivo: {str(e)}"
            )

        # Crear el registro en la base de datos
        attachment_data = {
            "file_name": filename,
            "file_path": file_path,
            "file_type": file_type,
            "file_size": file_size,
        }

        # Asignar el ID del padre apropiado
        if parent_type == "project":
            attachment_data["project_id"] = parent_id
        elif parent_type == "phase":
            attachment_data["phase_id"] = parent_id
        elif parent_type == "task":
            attachment_data["task_id"] = parent_id

        attachment_create = AttachmentCreate(**attachment_data)

        try:
            attachment = self.attachment_repository.create_attachment(
                db, attachment_create
            )
            db.commit()
            db.refresh(attachment)
            return attachment

        except Exception as e:
            # Si falla la creación en BD, eliminar el archivo
            FileUtils.delete_file(file_path)
            db.rollback()
            print(f"Error al crear el registro del adjunto: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error al crear el registro del adjunto",
            )

    def get_attachment_by_parent(
        self,
        db: Session,
        parent_type: str,
        parent_id: int,
        user_id: int,
    ) -> Optional[Attachment]:
        """
        Obtener el adjunto de una entidad padre

        Args:
            db: Sesión de base de datos
            parent_type: Tipo de padre ('project', 'phase', 'task')
            parent_id: ID del padre
            user_id: ID del usuario

        Returns:
            Optional[Attachment]: El adjunto o None si no existe

        Raises:
            HTTPException: Si hay errores de validación o permisos
        """
        # Validar que la entidad padre existe y pertenece al usuario
        self._validate_parent_entity(db, parent_type, parent_id, user_id)

        return self.attachment_repository.get_attachment_by_parent(
            db, parent_id, parent_type
        )

    def update_attachment(
        self,
        db: Session,
        attachment_id: int,
        attachment_update: AttachmentUpdate,
        user_id: int,
    ) -> Attachment:
        """
        Actualizar un adjunto existente

        Args:
            db: Sesión de base de datos
            attachment_id: ID del adjunto
            attachment_update: Datos a actualizar
            user_id: ID del usuario

        Returns:
            Attachment: El adjunto actualizado

        Raises:
            HTTPException: Si hay errores de validación o permisos
        """
        # Obtener el adjunto
        attachment = self.attachment_repository.get(db, attachment_id)
        if not attachment:
            raise HTTPException(status_code=404, detail="Adjunto no encontrado")

        # Determinar el tipo y ID del padre
        parent_type, parent_id = self._get_parent_info(attachment)

        # Validar permisos
        self._validate_parent_entity(db, parent_type, parent_id, user_id)

        # Actualizar el adjunto
        updated_attachment = self.attachment_repository.update_attachment(
            db, attachment_id, attachment_update
        )

        if not updated_attachment:
            raise HTTPException(status_code=404, detail="Adjunto no encontrado")

        db.commit()
        db.refresh(updated_attachment)
        return updated_attachment

    def delete_attachment(
        self,
        db: Session,
        attachment_id: int,
        user_id: int,
    ) -> bool:
        """
        Eliminar un adjunto

        Args:
            db: Sesión de base de datos
            attachment_id: ID del adjunto
            user_id: ID del usuario

        Returns:
            bool: True si se eliminó correctamente

        Raises:
            HTTPException: Si hay errores de validación o permisos
        """
        # Obtener el adjunto
        attachment = self.attachment_repository.get(db, attachment_id)
        if not attachment:
            raise HTTPException(status_code=404, detail="Adjunto no encontrado")

        # Determinar el tipo y ID del padre
        parent_type, parent_id = self._get_parent_info(attachment)

        # Validar permisos
        self._validate_parent_entity(db, parent_type, parent_id, user_id)

        # Eliminar el archivo físico
        FileUtils.delete_file(str(attachment.file_path))

        # Eliminar el registro de la base de datos
        deleted = self.attachment_repository.remove(db, id=attachment_id)

        if deleted:
            db.commit()
            return True

        db.rollback()
        raise HTTPException(status_code=500, detail="Error al eliminar el adjunto")

    def replace_attachment(
        self,
        db: Session,
        file: UploadFile,
        parent_type: str,
        parent_id: int,
        user_id: int,
    ) -> Attachment:
        """
        Reemplazar un documento existente

        Args:
            db: Sesión de base de datos
            file: Nuevo archivo
            parent_type: Tipo de padre ('project', 'phase', 'task')
            parent_id: ID del padre
            user_id: ID del usuario

        Returns:
            Attachment: El nuevo adjunto

        Raises:
            HTTPException: Si hay errores de validación o permisos
        """
        # 1. Validar que la entidad padre existe y pertenece al usuario
        self._validate_parent_entity(db, parent_type, parent_id, user_id)

        # 2. Obtener el adjunto existente
        existing_attachment = self.attachment_repository.get_attachment_by_parent(
            db, parent_id, parent_type
        )

        if not existing_attachment:
            raise HTTPException(
                status_code=404,
                detail=f"No existe un documento adjunto para esta {parent_type}",
            )

        # 3. Obtener información del archivo y validar tipo/tamaño
        filename, file_size, _ = FileUtils.get_file_info(file)

        # Validar tipo de archivo
        try:
            file_type = FileUtils.validate_file_type(file)
        except FileValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Validar tamaño del archivo
        try:
            FileUtils.validate_file_size(file_size)
        except FileValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # 4. Generar nombre único y construir ruta para el nuevo archivo
        unique_filename = FileUtils.generate_unique_filename(filename)
        parent_type_plural = self._get_parent_type_plural(parent_type)
        new_file_path = FileUtils.build_file_path(
            parent_type_plural, parent_id, unique_filename
        )

        # Asegurar que el directorio existe
        FileUtils.ensure_upload_directory()

        # 5. Guardar nuevo archivo en ruta única
        try:
            self._save_file(file, new_file_path)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error al guardar el archivo: {str(e)}"
            )

        # Guardamos la ruta anterior para eliminarla después del commit
        old_file_path = str(existing_attachment.file_path)

        # 6. Actualizar el mismo registro del adjunto (file_name, file_path, file_type, file_size)
        existing_attachment.file_name = filename
        existing_attachment.file_path = new_file_path
        existing_attachment.file_type = file_type
        existing_attachment.file_size = file_size

        # 7. Commit; si falla, borrar el nuevo archivo y rollback
        try:
            db.add(existing_attachment)
            db.commit()
            db.refresh(existing_attachment)
        except Exception as e:
            # Eliminar el nuevo archivo que acabamos de guardar
            FileUtils.delete_file(new_file_path)
            db.rollback()
            print(f"Error al actualizar el registro del adjunto: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error al actualizar el registro del adjunto",
            )

        # 8. Luego de commit, borrar el archivo anterior
        if not FileUtils.delete_file(old_file_path):
            # No fallamos la petición si no se puede borrar el archivo anterior físico, pero lo logueamos.
            print(
                f"Advertencia: No se pudo eliminar el archivo anterior {old_file_path}"
            )

        return existing_attachment

    def _validate_parent_entity(
        self, db: Session, parent_type: str, parent_id: int, user_id: int
    ) -> None:
        """
        Validar que la entidad padre existe y pertenece al usuario

        Args:
            db: Sesión de base de datos
            parent_type: Tipo de padre
            parent_id: ID del padre
            user_id: ID del usuario

        Raises:
            HTTPException: Si la entidad no existe o no pertenece al usuario
        """
        entity_map = {
            "project": (self.project_repository, "Proyecto"),
            "phase": (self.phase_repository, "Fase"),
            "task": (self.task_repository, "Tarea"),
        }
        if parent_type not in entity_map:
            raise HTTPException(
                status_code=400,
                detail="Tipo de entidad padre no válido. Use: 'project', 'phase' o 'task'",
            )

        repository, entity_name = entity_map[parent_type]
        entity = repository.get(db, parent_id)

        if not entity:
            raise HTTPException(status_code=404, detail=f"{entity_name} no encontrado")

        # Verificar permisos según el tipo de entidad
        if parent_type == "project":
            # Para proyectos, verificar owner_id
            if hasattr(entity, "owner_id") and getattr(entity, "owner_id") != user_id:
                raise HTTPException(
                    status_code=403,
                    detail=f"No tiene permisos para acceder a este {entity_name.lower()}",
                )
            return

        if parent_type == "phase":
            # Para fases, verificar que el proyecto padre pertenezca al usuario
            if hasattr(entity, "project_id"):
                project = self.project_repository.get(db, getattr(entity, "project_id"))
                if project and hasattr(project, "owner_id"):
                    if getattr(project, "owner_id") != user_id:
                        raise HTTPException(
                            status_code=403,
                            detail=f"No tiene permisos para acceder a esta {entity_name.lower()}",
                        )
                elif not project:
                    raise HTTPException(
                        status_code=403,
                        detail=f"No tiene permisos para acceder a esta {entity_name.lower()}",
                    )
            return

        # Para tareas, verificar que la fase padre pertenezca a un proyecto del usuario
        if hasattr(entity, "phase_id"):
            phase = self.phase_repository.get(db, getattr(entity, "phase_id"))
            if phase and hasattr(phase, "project_id"):
                project = self.project_repository.get(db, getattr(phase, "project_id"))
                if project and hasattr(project, "owner_id"):
                    if getattr(project, "owner_id") != user_id:
                        raise HTTPException(
                            status_code=403,
                            detail=f"No tiene permisos para acceder a esta {entity_name.lower()}",
                        )
                elif not project:
                    raise HTTPException(
                        status_code=403,
                        detail=f"No tiene permisos para acceder a esta {entity_name.lower()}",
                    )

    def _get_parent_info(self, attachment: Attachment) -> tuple[str, int]:
        """
        Obtener información del padre de un adjunto

        Args:
            attachment: El adjunto

        Returns:
            tuple[str, int]: (tipo_padre, id_padre)
        """
        if attachment.project_id is not None:
            return "project", attachment.project_id  # type: ignore
        elif attachment.phase_id is not None:
            return "phase", attachment.phase_id  # type: ignore
        elif attachment.task_id is not None:
            return "task", attachment.task_id  # type: ignore
        else:
            raise ValueError("Adjunto sin entidad padre válida")

    def _get_parent_type_plural(self, parent_type: str) -> str:
        """
        Obtener la forma plural del tipo de padre para rutas de archivos

        Args:
            parent_type: Tipo de padre

        Returns:
            str: Forma plural
        """
        parent_type_map = {
            "project": "projects",
            "phase": "phases",
            "task": "tasks",
        }
        try:
            return parent_type_map[parent_type]
        except KeyError as exc:
            raise ValueError(f"Tipo de padre no válido: {parent_type}") from exc

    def _save_file(self, file: UploadFile, file_path: str) -> None:
        """
        Guardar el archivo en el sistema de archivos

        Args:
            file: Archivo a guardar
            file_path: Ruta donde guardar el archivo

        Raises:
            Exception: Si hay error al guardar el archivo
        """
        try:
            # Crear directorios si no existen
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            # Guardar el archivo
            with open(file_path, "wb") as buffer:
                file.file.seek(0)  # Asegurar que estamos al inicio del archivo
                buffer.write(file.file.read())
        except Exception as e:
            raise Exception(f"Error al guardar archivo: {str(e)}")


# Instancia del servicio para usar en endpoints
attachment_service = AttachmentService()
