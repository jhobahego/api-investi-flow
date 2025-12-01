from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ProjectStatus(str, Enum):
    """Estados posibles de un proyecto"""

    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ResearchType(str, Enum):
    """Tipos de investigación"""

    BASIC = "basic"
    APPLIED = "applied"
    EXPERIMENTAL = "experimental"
    THEORETICAL = "theoretical"
    QUALITATIVE = "qualitative"
    QUANTITATIVE = "quantitative"
    MIXED = "mixed"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    research_type = Column(
        String(50), nullable=True
    )  # Almacenar como string en lugar de Enum
    institution = Column(String(255), nullable=True)
    research_group = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)
    status = Column(
        String(50), default=ProjectStatus.PLANNING.value, nullable=False
    )  # Almacenar como string
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
    owner = relationship("User", back_populates="projects")
    phases = relationship(
        "Phase",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Phase.position",
    )
    attachment = relationship(
        "Attachment",
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
    )
    conversations = relationship(
        "Conversation", back_populates="project", cascade="all, delete-orphan"
    )
    # bibliographies = relationship("Bibliography", back_populates="project", cascade="all, delete-orphan")
