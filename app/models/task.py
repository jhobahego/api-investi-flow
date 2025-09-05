from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class TaskStatus(str, Enum):
    """Estados posibles de una tarea"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    position = Column(Integer, nullable=False)

    status = Column(
        SqlEnum(TaskStatus), default=TaskStatus.PENDING.value, nullable=False
    )
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    completed = Column(Boolean, default=False, nullable=False)
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

    # Foreign Keys
    phase_id = Column(Integer, ForeignKey("phases.id"), nullable=False)

    # Relaciones
    phase = relationship("Phase", back_populates="tasks")
    attachment = relationship(
        "Attachment",
        back_populates="task",
        cascade="all, delete-orphan",
        uselist=False,
    )
