from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import CheckConstraint, Column, DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class FileType(str, Enum):
    """Tipos de archivo comunes"""

    PDF = "pdf"
    DOCX = "docx"


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(SqlEnum(FileType), nullable=False)
    file_size = Column(Integer, nullable=False)  # Tamaño en bytes
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Foreign Keys for polymorphic association
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, unique=True)
    phase_id = Column(Integer, ForeignKey("phases.id"), nullable=True, unique=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, unique=True)

    # Relaciones
    project = relationship("Project", back_populates="attachment")
    phase = relationship("Phase", back_populates="attachment")
    task = relationship("Task", back_populates="attachment")

    __table_args__ = (
        CheckConstraint(
            "(project_id IS NOT NULL AND phase_id IS NULL AND task_id IS NULL) OR "
            "(project_id IS NULL AND phase_id IS NOT NULL AND task_id IS NULL) OR "
            "(project_id IS NULL AND phase_id IS NULL AND task_id IS NOT NULL)",
            name="ck_attachment_parent_exclusive",
        ),
    )
