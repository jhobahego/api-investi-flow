from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.phase import Phase
    from app.models.project import Project
    from app.models.task import Task


class FileType(str, Enum):
    """Tipos de archivo comunes"""

    PDF = "pdf"
    DOCX = "docx"


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[FileType] = mapped_column(SqlEnum(FileType), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # Tamaño en bytes
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Foreign Keys for polymorphic association
    project_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=True, unique=True
    )
    phase_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("phases.id"), nullable=True, unique=True
    )
    task_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tasks.id"), nullable=True, unique=True
    )

    # Relaciones
    project: Mapped[Optional["Project"]] = relationship(
        "Project", back_populates="attachment"
    )
    phase: Mapped[Optional["Phase"]] = relationship(
        "Phase", back_populates="attachment"
    )
    task: Mapped[Optional["Task"]] = relationship("Task", back_populates="attachment")

    __table_args__ = (
        CheckConstraint(
            "(project_id IS NOT NULL AND phase_id IS NULL AND task_id IS NULL) OR "
            "(project_id IS NULL AND phase_id IS NOT NULL AND task_id IS NULL) OR "
            "(project_id IS NULL AND phase_id IS NULL AND task_id IS NOT NULL)",
            name="ck_attachment_parent_exclusive",
        ),
    )
