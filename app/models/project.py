from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.attachment import Attachment
from app.models.bibliography import Bibliography
from app.models.conversation import Conversation
from app.models.phase import Phase
from app.models.user import User


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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    research_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # Almacenar como string en lugar de Enum
    institution: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    research_group: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=ProjectStatus.PLANNING.value, nullable=False
    )  # Almacenar como string
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
    owner: Mapped["User"] = relationship("User", back_populates="projects")
    phases: Mapped[list["Phase"]] = relationship(
        "Phase",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Phase.position",
    )
    attachment: Mapped[Optional["Attachment"]] = relationship(
        "Attachment",
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="project", cascade="all, delete-orphan"
    )
    bibliographies: Mapped[list["Bibliography"]] = relationship(
        "Bibliography", back_populates="project", cascade="all, delete-orphan"
    )
