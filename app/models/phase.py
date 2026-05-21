from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.attachment import Attachment
from app.models.project import Project
from app.models.task import Task


class Phase(Base):
    __tablename__ = "phases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relaciones con otras tablas
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False
    )
    project: Mapped["Project"] = relationship("Project", back_populates="phases")

    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="phase", cascade="all, delete-orphan"
    )

    # Relación uno a uno con Attachment para adjuntar un documento a una fase
    attachment: Mapped[Optional["Attachment"]] = relationship(
        "Attachment",
        back_populates="phase",
        cascade="all, delete-orphan",
        uselist=False,
    )
