from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Project


class Bibliography(Base):
    __tablename__ = "bibliographies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False, index=True
    )

    # Campos básicos APA 7
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # libro, articulo, web, tesis, etc.
    author: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON string o texto formateado de autores
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Editorial, Revista, Sitio Web, etc.

    # Campos adicionales
    doi: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    volume: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    issue: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    pages: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Archivo adjunto
    file_path: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )  # Ruta al archivo PDF/DOCX
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

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

    # Relaciones
    project: Mapped["Project"] = relationship(
        "Project", back_populates="bibliographies"
    )
