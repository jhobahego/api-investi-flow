"""
Schemas para conversaciones y mensajes de chat
"""
from datetime import datetime

from pydantic import BaseModel, Field

# =============================================================================
# SCHEMAS PARA MENSAJES
# =============================================================================


class MessageBase(BaseModel):
    """Schema base para mensajes"""

    role: str = Field(..., description="Rol del mensaje: 'user' o 'model'")
    content: str = Field(..., description="Contenido del mensaje")


class MessageCreate(MessageBase):
    """Schema para crear un mensaje"""

    conversation_id: int = Field(..., description="ID de la conversación")


class MessageResponse(MessageBase):
    """Schema para respuesta de mensaje"""

    id: int
    conversation_id: int
    model_used: str | None = Field(
        None, description="Modelo de IA utilizado (solo para mensajes del asistente)"
    )
    created_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# SCHEMAS PARA CONVERSACIONES
# =============================================================================


class ConversationBase(BaseModel):
    """Schema base para conversaciones"""

    title: str = Field(
        default="Nueva conversación", description="Título de la conversación"
    )


class ConversationCreate(ConversationBase):
    """Schema para crear una conversación"""

    project_id: int = Field(..., description="ID del proyecto")


class ConversationUpdate(BaseModel):
    """Schema para actualizar una conversación"""

    title: str | None = Field(None, description="Nuevo título de la conversación")


class ConversationResponse(ConversationBase):
    """Schema para respuesta de conversación"""

    id: int
    project_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ConversationListResponse(ConversationBase):
    """Schema para listar conversaciones (sin mensajes completos)"""

    id: int
    project_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    message_count: int = Field(0, description="Número de mensajes en la conversación")
    last_message_preview: str | None = Field(
        None, description="Preview del último mensaje"
    )

    model_config = {"from_attributes": True}


# =============================================================================
# SCHEMA PARA CHAT (COMPATIBILIDAD CON ENDPOINT EXISTENTE)
# =============================================================================


class ChatWithHistoryRequest(BaseModel):
    """Request para chat con historial persistente"""

    message: str = Field(..., description="Mensaje del usuario")
    conversation_id: int | None = Field(
        None,
        description="ID de conversación existente (si no se provee, se crea una nueva)",
    )
    title: str | None = Field(
        None, description="Título para nueva conversación (opcional)"
    )


class ChatWithHistoryResponse(BaseModel):
    """Response para chat con historial persistente"""

    response: str = Field(..., description="Respuesta del asistente")
    model_used: str = Field(..., description="Modelo de IA utilizado")
    conversation_id: int = Field(..., description="ID de la conversación")
    message_id: int = Field(..., description="ID del mensaje de respuesta")
