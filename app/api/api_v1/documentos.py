"""
Endpoints para extracción y gestión de contenido de documentos
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.attachment_repository import AttachmentRepository
from app.schemas.document import (
    DocumentContentResponse,
    DocumentPagesResponse,
    DocumentPreviewResponse,
)
from app.services.document_extraction_service import document_extraction_service

router = APIRouter(prefix="/documentos", tags=["documentos"])

attachment_repository = AttachmentRepository()


@router.get("/{attachment_id}/extract-content", response_model=DocumentContentResponse)
async def extract_document_content(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Extrae el contenido de un documento .docx y lo convierte a HTML
    compatible con TipTap editor

    Args:
        attachment_id: ID del adjunto/documento
        db: Sesión de base de datos
        current_user: Usuario autenticado

    Returns:
        Dict con el contenido HTML y metadatos del documento

    Raises:
        HTTPException 404: Si el documento no existe
        HTTPException 403: Si el usuario no tiene permisos
        HTTPException 400: Si el formato no es .docx
        HTTPException 500: Si hay error en la extracción
    """
    # Obtener el adjunto
    attachment = attachment_repository.get(db, attachment_id)

    if not attachment:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # Validar permisos (verificar que el usuario es dueño del proyecto padre)
    from app.services.attachment_service import attachment_service

    parent_type, parent_id = attachment_service._get_parent_info(attachment)

    try:
        attachment_service._validate_parent_entity(
            db, parent_type, parent_id, current_user.id
        )
    except HTTPException:
        raise HTTPException(
            status_code=403, detail="No tiene permisos para acceder a este documento"
        )

    # Validar tipo de archivo
    if attachment.file_type.lower() not in [
        "docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]:
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden extraer contenidos de archivos .docx",
        )

    # Extraer contenido
    html_content = document_extraction_service.extract_docx_to_html(
        str(attachment.file_path)
    )

    # Convertir attachment a dict y agregar html_content
    response_data = {
        "id": attachment.id,
        "file_name": attachment.file_name,
        "file_type": attachment.file_type,
        "file_size": attachment.file_size,
        "file_path": attachment.file_path,
        "project_id": attachment.project_id,
        "phase_id": attachment.phase_id,
        "task_id": attachment.task_id,
        "created_at": attachment.created_at,
        "updated_at": attachment.updated_at,
        "html_content": html_content,  # Campo adicional
    }

    return DocumentContentResponse(**response_data)


@router.get("/{attachment_id}/preview", response_model=DocumentPreviewResponse)
async def get_document_preview(
    attachment_id: int,
    max_chars: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene una vista previa en texto plano del documento

    Args:
        attachment_id: ID del adjunto/documento
        max_chars: Número máximo de caracteres (default: 200)
        db: Sesión de base de datos
        current_user: Usuario autenticado

    Returns:
        Dict con la vista previa del documento

    Raises:
        HTTPException 404: Si el documento no existe
        HTTPException 403: Si el usuario no tiene permisos
    """
    # Obtener el adjunto
    attachment = attachment_repository.get(db, attachment_id)

    if not attachment:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # Validar permisos
    from app.services.attachment_service import attachment_service

    parent_type, parent_id = attachment_service._get_parent_info(attachment)

    try:
        attachment_service._validate_parent_entity(
            db, parent_type, parent_id, current_user.id
        )
    except HTTPException:
        raise HTTPException(
            status_code=403, detail="No tiene permisos para acceder a este documento"
        )

    # Obtener vista previa
    preview = document_extraction_service.get_document_preview(
        str(attachment.file_path), max_chars=max_chars
    )

    return DocumentPreviewResponse(
        attachment_id=attachment_id,
        file_name=attachment.file_name,
        preview=preview,
        max_chars=max_chars,
    )


@router.get("/{attachment_id}/extract-pages", response_model=DocumentPagesResponse)
async def extract_document_pages(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Extrae el contenido de un documento .docx dividido en páginas HTML

    Args:
        attachment_id: ID del adjunto/documento
        db: Sesión de base de datos
        current_user: Usuario autenticado

    Returns:
        Dict con las páginas HTML y metadatos del documento

    Raises:
        HTTPException 404: Si el documento no existe
        HTTPException 403: Si el usuario no tiene permisos
        HTTPException 400: Si el formato no es .docx
        HTTPException 500: Si hay error en la extracción
    """
    # Obtener el adjunto
    attachment = attachment_repository.get(db, attachment_id)

    if not attachment:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # Validar permisos
    from app.services.attachment_service import attachment_service

    parent_type, parent_id = attachment_service._get_parent_info(attachment)

    try:
        attachment_service._validate_parent_entity(
            db, parent_type, parent_id, current_user.id
        )
    except HTTPException:
        raise HTTPException(
            status_code=403, detail="No tiene permisos para acceder a este documento"
        )

    # Validar tipo de archivo
    if attachment.file_type.lower() not in [
        "docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]:
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden extraer contenidos de archivos .docx",
        )

    # Extraer contenido en páginas
    pages = document_extraction_service.extract_docx_to_pages(str(attachment.file_path))

    # Convertir attachment a dict y agregar páginas
    response_data = {
        "id": attachment.id,
        "file_name": attachment.file_name,
        "file_type": attachment.file_type,
        "file_size": attachment.file_size,
        "file_path": attachment.file_path,
        "project_id": attachment.project_id,
        "phase_id": attachment.phase_id,
        "task_id": attachment.task_id,
        "created_at": attachment.created_at,
        "updated_at": attachment.updated_at,
        "pages": pages,
        "total_pages": len(pages),
    }

    return DocumentPagesResponse(**response_data)
