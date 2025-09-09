from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Phase(Base):
    __tablename__ = "phases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    position = Column(Integer, nullable=False)
    color = Column(String, nullable=True)

    # Relaciones con otras tablas
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    project = relationship("Project", back_populates="phases")

    tasks = relationship("Task", back_populates="phase", cascade="all, delete-orphan")

    # Relación uno a uno con Attachment para adjuntar un documento a una fase
    attachment = relationship(
        "Attachment",
        back_populates="phase",
        cascade="all, delete-orphan",
        uselist=False,
    )
