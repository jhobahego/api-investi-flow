from typing import Optional

from sqlalchemy.orm import Session

from app.models.attachment import Attachment
from app.repositories.base import BaseRepository
from app.schemas.attachment import AttachmentCreate, AttachmentUpdate


class AttachmentRepository(
    BaseRepository[Attachment, AttachmentCreate, AttachmentUpdate]
):
    """Repositorio simplificado para la gestión de adjuntos"""

    def __init__(self) -> None:
        super().__init__(Attachment)

    def get_attachment_by_parent(
        self, db: Session, parent_id: int, parent_type: str
    ) -> Optional[Attachment]:
        """
        Obtener el adjunto por ID del padre (proyecto, fase o tarea)

        Args:
            db: Sesión de base de datos
            parent_id: ID del padre (proyecto, fase o tarea)
            parent_type: Tipo de padre ('project', 'phase' o 'task')

        Returns:
            Optional[Attachment]: El adjunto asociado al padre especificado o None

        Raises:
            ValueError: Si el tipo de padre no es válido
        """
        if parent_type == "project":
            return (
                db.query(self.model).filter(Attachment.project_id == parent_id).first()
            )
        elif parent_type == "phase":
            return db.query(self.model).filter(Attachment.phase_id == parent_id).first()
        elif parent_type == "task":
            return db.query(self.model).filter(Attachment.task_id == parent_id).first()
        else:
            raise ValueError(
                "Tipo de padre no válido. Use: 'project', 'phase' o 'task'"
            )

    def create_attachment(
        self, db: Session, attachment_in: AttachmentCreate
    ) -> Attachment:
        """
        Crear un nuevo adjunto

        Args:
            db: Sesión de base de datos
            attachment_in: Datos del adjunto a crear

        Returns:
            Attachment: El adjunto creado
        """
        attachment_data = attachment_in.model_dump()
        attachment = Attachment(**attachment_data)
        db.add(attachment)
        return attachment

    def update_attachment(
        self, db: Session, attachment_id: int, attachment_in: AttachmentUpdate
    ) -> Optional[Attachment]:
        """
        Actualizar un adjunto existente

        Args:
            db: Sesión de base de datos
            attachment_id: ID del adjunto a actualizar
            attachment_in: Datos actualizados del adjunto

        Returns:
            Optional[Attachment]: El adjunto actualizado o None si no existe
        """
        attachment = self.get(db, attachment_id)
        if not attachment:
            return None

        update_data = attachment_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(attachment, field, value)

        db.add(attachment)
        return attachment

    def delete_attachment_by_parent(
        self, db: Session, parent_id: int, parent_type: str
    ) -> bool:
        """
        Eliminar el adjunto por ID del padre (proyecto, fase o tarea)

        Args:
            db: Sesión de base de datos
            parent_id: ID del padre (proyecto, fase o tarea)
            parent_type: Tipo de padre ('project', 'phase' o 'task')

        Returns:
            bool: True si se eliminó el adjunto, False si no existía
        """
        attachment = self.get_attachment_by_parent(db, parent_id, parent_type)
        if not attachment:
            return False

        db.delete(attachment)
        return True

    def has_attachment(self, db: Session, parent_id: int, parent_type: str) -> bool:
        """
        Verificar si el padre (proyecto, fase o tarea) tiene un adjunto

        Args:
            db: Sesión de base de datos
            parent_id: ID del padre (proyecto, fase o tarea)
            parent_type: Tipo de padre ('project', 'phase' o 'task')

        Returns:
            bool: True si tiene adjunto, False si no
        """
        return self.get_attachment_by_parent(db, parent_id, parent_type) is not None
