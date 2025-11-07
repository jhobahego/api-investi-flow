"""
Schemas para extracción y gestión de documentos
Extiende los schemas de attachment para incluir contenido HTML
"""
from typing import List

from pydantic import BaseModel, Field

from app.schemas.attachment import AttachmentResponse


class DocumentContentResponse(AttachmentResponse):
    """
    Respuesta con el contenido extraído de un documento
    Extiende AttachmentResponse agregando el contenido HTML
    """

    html_content: str = Field(..., description="Contenido HTML del documento")


class DocumentPagesResponse(AttachmentResponse):
    """
    Respuesta con el contenido extraído de un documento dividido en páginas
    Extiende AttachmentResponse agregando las páginas HTML
    """

    pages: List[str] = Field(..., description="Lista de páginas HTML del documento")
    total_pages: int = Field(..., description="Número total de páginas")


class DocumentPreviewResponse(BaseModel):
    """Respuesta con la vista previa de un documento"""

    attachment_id: int = Field(..., description="ID del adjunto")
    file_name: str = Field(..., description="Nombre del archivo")
    preview: str = Field(..., description="Vista previa del contenido")
    max_chars: int = Field(..., description="Número máximo de caracteres")

    model_config = {"from_attributes": True}
