"""
Repositorio para gestión de conversaciones y mensajes de chat
"""
import logging
from typing import Sequence

from sqlalchemy import desc, func
from sqlalchemy.orm import Session, joinedload

from app.models.conversation import Conversation, Message
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
)

logger = logging.getLogger(__name__)


class ConversationRepository:
    """Repositorio para operaciones CRUD de conversaciones"""

    def __init__(self):
        self.model = Conversation

    def get_by_project_and_user(
        self,
        db: Session,
        project_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Conversation]:
        """
        Obtiene todas las conversaciones de un proyecto para un usuario específico.

        Args:
            db: Sesión de base de datos
            project_id: ID del proyecto
            user_id: ID del usuario
            skip: Número de registros a saltar (paginación)
            limit: Número máximo de registros a retornar

        Returns:
            Lista de conversaciones ordenadas por última actualización
        """
        return (
            db.query(Conversation)
            .filter(
                Conversation.project_id == project_id, Conversation.user_id == user_id
            )
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_with_messages(
        self, db: Session, conversation_id: int, user_id: int
    ) -> Conversation | None:
        """
        Obtiene una conversación con todos sus mensajes.

        Args:
            db: Sesión de base de datos
            conversation_id: ID de la conversación
            user_id: ID del usuario (para validar permisos)

        Returns:
            Conversación con mensajes o None si no existe o no pertenece al usuario
        """
        return (
            db.query(Conversation)
            .options(joinedload(Conversation.messages))
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .first()
        )

    def create_conversation(
        self,
        db: Session,
        project_id: int,
        user_id: int,
        title: str = "Nueva conversación",
    ) -> Conversation:
        """
        Crea una nueva conversación.

        Args:
            db: Sesión de base de datos
            project_id: ID del proyecto
            user_id: ID del usuario propietario
            title: Título de la conversación

        Returns:
            Conversación creada
        """
        conversation = Conversation(project_id=project_id, user_id=user_id, title=title)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        logger.info(
            f"Conversación creada: ID={conversation.id}, proyecto={project_id}, usuario={user_id}"
        )
        return conversation

    def update_title(
        self, db: Session, conversation_id: int, user_id: int, new_title: str
    ) -> Conversation | None:
        """
        Actualiza el título de una conversación.

        Args:
            db: Sesión de base de datos
            conversation_id: ID de la conversación
            user_id: ID del usuario (validación de permisos)
            new_title: Nuevo título

        Returns:
            Conversación actualizada o None si no existe o no pertenece al usuario
        """
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .first()
        )

        if not conversation:
            return None

        conversation.title = new_title
        db.commit()
        db.refresh(conversation)
        logger.info(
            f"Título de conversación {conversation_id} actualizado a '{new_title}'"
        )
        return conversation

    def delete(self, db: Session, *, id: int) -> bool:
        """
        Elimina una conversación por ID.

        Args:
            db: Sesión de base de datos
            id: ID de la conversación

        Returns:
            True si se eliminó, False si no existía
        """
        conversation = db.query(Conversation).filter(Conversation.id == id).first()
        if not conversation:
            return False

        db.delete(conversation)
        db.commit()
        logger.info(f"Conversación {id} eliminada")
        return True

    def get_message_count(self, db: Session, conversation_id: int) -> int:
        """
        Cuenta el número de mensajes en una conversación.

        Args:
            db: Sesión de base de datos
            conversation_id: ID de la conversación

        Returns:
            Número de mensajes
        """
        return (
            db.query(func.count(Message.id))
            .filter(Message.conversation_id == conversation_id)
            .scalar()
            or 0
        )


class MessageRepository:
    """Repositorio para operaciones CRUD de mensajes"""

    def __init__(self):
        self.model = Message

    def create_message(
        self,
        db: Session,
        conversation_id: int,
        role: str,
        content: str,
        model_used: str | None = None,
    ) -> Message:
        """
        Crea un nuevo mensaje en una conversación.

        Args:
            db: Sesión de base de datos
            conversation_id: ID de la conversación
            role: Rol del mensaje ('user' o 'model')
            content: Contenido del mensaje
            model_used: Modelo de IA utilizado (solo para mensajes del asistente)

        Returns:
            Mensaje creado
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model_used=model_used,
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        logger.info(
            f"Mensaje creado: ID={message.id}, conversación={conversation_id}, rol={role}"
        )
        return message

    def get_conversation_messages(
        self, db: Session, conversation_id: int
    ) -> Sequence[Message]:
        """
        Obtiene todos los mensajes de una conversación ordenados por fecha.

        Args:
            db: Sesión de base de datos
            conversation_id: ID de la conversación

        Returns:
            Lista de mensajes ordenados cronológicamente
        """
        return (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .all()
        )

    def get_last_message(self, db: Session, conversation_id: int) -> Message | None:
        """
        Obtiene el último mensaje de una conversación.

        Args:
            db: Sesión de base de datos
            conversation_id: ID de la conversación

        Returns:
            Último mensaje o None si la conversación está vacía
        """
        return (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .first()
        )


# Instancias globales de los repositorios
conversation_repository = ConversationRepository()
message_repository = MessageRepository()
