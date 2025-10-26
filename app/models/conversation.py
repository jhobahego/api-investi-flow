"""
Modelos para conversaciones de chat con IA
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Conversation(Base):
    """
    Modelo para conversaciones de chat con el asistente IA.
    Una conversación pertenece a un proyecto y un usuario.
    """

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, default="Nueva conversación")
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relaciones
    project = relationship("Project", back_populates="conversations")
    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    """
    Modelo para mensajes individuales en una conversación.
    Cada mensaje tiene un rol ('user' o 'model') y contenido.
    """

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(10), nullable=False)  # 'user' o 'model' (asistente IA)
    content = Column(Text, nullable=False)
    model_used = Column(
        String(100), nullable=True
    )  # Modelo de IA utilizado (solo para mensajes de 'model')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    conversation = relationship("Conversation", back_populates="messages")
