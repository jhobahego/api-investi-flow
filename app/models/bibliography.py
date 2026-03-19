from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Bibliography(Base):
    __tablename__ = "bibliographies"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    # Campos básicos APA 7
    type = Column(String(50), nullable=False)  # libro, articulo, web, tesis, etc.
    author = Column(Text, nullable=False)  # JSON string o texto formateado de autores
    year = Column(Integer, nullable=True)
    title = Column(Text, nullable=False)
    source = Column(Text, nullable=True)  # Editorial, Revista, Sitio Web, etc.

    # Campos adicionales
    doi = Column(String(255), nullable=True)
    url = Column(Text, nullable=True)
    volume = Column(String(50), nullable=True)
    issue = Column(String(50), nullable=True)
    pages = Column(String(50), nullable=True)

    # Archivo adjunto
    file_path = Column(String(512), nullable=True)  # Ruta al archivo PDF/DOCX
    file_name = Column(String(255), nullable=True)

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

    # Relaciones
    project = relationship("Project", back_populates="bibliographies")
