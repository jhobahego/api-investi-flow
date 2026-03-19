import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.ai_config import UserPlan
from app.core.ai_prompts import format_bibliography_context, format_project_context
from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.repositories.bibliography_repository import bibliography_repository
from app.repositories.conversation_repository import (
    conversation_repository,
    message_repository,
)
from app.schemas.ai import (
    AIErrorResponse,
    BibliographyRequest,
    BibliographyResponse,
    CitationRequest,
    CitationResponse,
    SuggestionRequest,
    SuggestionResponse,
)
from app.schemas.conversation import (
    ChatWithHistoryRequest,
    ChatWithHistoryResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
)
from app.services.ai_service import AIServiceError, ModelNotAvailableError, ai_service
from app.services.attachment_service import attachment_service
from app.services.document_extraction_service import document_extraction_service
from app.services.project_service import project_service

logger = logging.getLogger(__name__)

router = APIRouter()
project_router = APIRouter()


# =============================================================================
# ENDPOINT: SUGERENCIAS DE TEXTO
# =============================================================================


@router.post(
    "/sugerencias",
    response_model=SuggestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Generar sugerencias de texto",
    description="""
    Genera sugerencias de autocompletado de texto para el editor.

    Este endpoint recibe:
    - El texto actual donde el usuario solicita la sugerencia
    - El contenido completo del documento
    - La bibliografía disponible en el proyecto (opcional)
    - Información del proyecto (opcional)

    Devuelve una sugerencia de continuación coherente y académica que puede
    incluir citaciones de las fuentes bibliográficas proporcionadas.

    **Nota**: Este endpoint está disponible para todos los planes.
    El modelo utilizado depende del plan del usuario (hardcodeado por ahora).
    """,
    responses={
        200: {
            "description": "Sugerencia generada exitosamente",
            "model": SuggestionResponse,
        },
        401: {"description": "No autorizado - Token inválido o ausente"},
        403: {
            "description": "Funcionalidad no disponible para el plan del usuario",
            "model": AIErrorResponse,
        },
        500: {
            "description": "Error interno del servidor o del servicio de IA",
            "model": AIErrorResponse,
        },
    },
)
async def generate_suggestion(
    request: SuggestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SuggestionResponse:
    """
    Genera sugerencias de texto basadas en el contexto del documento.

    Args:
        request: Datos de la solicitud (texto, documento, bibliografía)
        current_user: Usuario autenticado
        db: Sesión de base de datos

    Returns:
        SuggestionResponse: Sugerencia generada y modelo utilizado

    Raises:
        HTTPException: Si hay un error en el servicio de IA
    """
    try:
        logger.info(f"Usuario {current_user.email} solicita sugerencia de texto")

        # TODO: Determinar el plan del usuario desde la base de datos
        # Por ahora hardcodeamos el plan según el rol o usamos un plan por defecto
        user_plan = UserPlan.ESTUDIANTE  # Hardcodeado temporalmente

        # Formatear contexto del proyecto si está disponible
        project_context = None
        if request.project_info:
            project_context = format_project_context(
                project_name=request.project_info.get("name", "Proyecto sin nombre"),
                description=request.project_info.get("description"),
                research_type=request.project_info.get("research_type"),
            )

        # Convertir bibliografía a formato dict
        bibliography_list = (
            [ref.model_dump() for ref in request.bibliography]
            if request.bibliography
            else None
        )

        # Llamar al servicio de IA
        suggestion, model_used = await ai_service.suggest_text(
            text=request.text,
            document_content=request.document_content,
            bibliography=bibliography_list,
            project_context=project_context,
            plan=user_plan,
        )

        logger.info(f"Sugerencia generada exitosamente con modelo {model_used}")

        return SuggestionResponse(
            suggestion=suggestion,
            model_used=model_used,
        )

    except ModelNotAvailableError as e:
        logger.warning(
            f"Modelo no disponible para usuario {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "feature_not_available",
                "message": str(e),
                "details": {"feature": "suggestions", "plan": user_plan.value},
            },
        )

    except AIServiceError as e:
        logger.error(f"Error del servicio de IA: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ai_service_error",
                "message": "Error al generar la sugerencia. Por favor, intenta nuevamente.",
                "details": {"error_type": type(e).__name__},
            },
        )

    except Exception as e:
        logger.error(f"Error inesperado en sugerencias: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Error interno del servidor",
                "details": {},
            },
        )


# =============================================================================
# ENDPOINT: FORMATEO DE CITAS APA 7
# =============================================================================


@project_router.post(
    "/proyectos/{project_id}/ia/citas",
    response_model=CitationResponse,
    status_code=status.HTTP_200_OK,
    summary="Formatear cita bibliográfica en APA 7",
    description="""
    Genera una cita bibliográfica perfectamente formateada en estilo APA 7ma edición.

    Este endpoint recibe:
    - Datos de la fuente (tipo, autores, año, título, editorial/revista, etc.)
    - Contexto del proyecto (opcional, para verificar consistencia)
    - Bibliografía existente (opcional, para mantener formato consistente)

    Devuelve la cita formateada lista para usar en el documento.

    **Tipos de fuentes soportadas**:
    - `libro`: Libros completos
    - `articulo`: Artículos de revistas científicas
    - `capitulo`: Capítulos de libros editados
    - `tesis`: Tesis de grado, maestría o doctorado
    - `web`: Documentos o páginas web

    **Nota**: El endpoint requiere acceso al proyecto para mantener
    consistencia con la bibliografía existente.
    """,
    responses={
        200: {
            "description": "Cita formateada exitosamente",
            "model": CitationResponse,
        },
        401: {"description": "No autorizado - Token inválido o ausente"},
        403: {"description": "Sin acceso al proyecto"},
        404: {"description": "Proyecto no encontrado"},
        422: {"description": "Datos de la fuente inválidos o incompletos"},
        500: {
            "description": "Error interno del servidor o del servicio de IA",
            "model": AIErrorResponse,
        },
    },
)
async def format_citation(
    project_id: int,
    request: CitationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CitationResponse:
    """
    Formatea una cita bibliográfica en estilo APA 7.

    Args:
        project_id: ID del proyecto
        request: Datos de la fuente a formatear
        current_user: Usuario autenticado
        db: Sesión de base de datos

    Returns:
        CitationResponse: Cita formateada y modelo utilizado

    Raises:
        HTTPException: Si hay errores de autorización, proyecto no encontrado o del servicio de IA
    """
    try:
        logger.info(
            f"Usuario {current_user.email} solicita formateo de cita en proyecto {project_id}"
        )

        # Verificar que el proyecto existe y el usuario tiene acceso
        project = project_service.get_user_project_by_id(
            db,
            project_id=project_id,
            owner_id=current_user.id,  # type: ignore
        )
        if not project:
            logger.warning(f"Proyecto {project_id} no encontrado o usuario sin acceso")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto no encontrado o sin acceso",
            )

        # TODO: Determinar el plan del usuario desde la base de datos
        user_plan = UserPlan.ESTUDIANTE  # Plan por defecto para citas

        # Formatear contexto del proyecto
        project_context = format_project_context(
            project_name=project.name,  # type: ignore
            description=project.description,  # type: ignore
            research_type=project.research_type,  # type: ignore
        )

        # Convertir bibliografía del request a formato dict
        project_bibliography = (
            [ref.model_dump() for ref in request.project_bibliography]
            if request.project_bibliography
            else None
        )

        # Preparar datos de la cita
        citation_data = {
            "tipo": request.tipo,
            "autores": [autor.model_dump() for autor in request.autores],
            "anio": request.anio,
            "titulo": request.titulo,
            "editorial": request.editorial,
            "revista": request.revista,
            "volumen": request.volumen,
            "numero": request.numero,
            "paginas": request.paginas,
            "doi": request.doi,
            "url": request.url,
            "editor": request.editor,
            "titulo_libro": request.titulo_libro,
            "institucion": request.institucion,
        }

        # Llamar al servicio de IA
        citation, model_used = await ai_service.format_citation(
            citation_data=citation_data,
            project_bibliography=project_bibliography,
            project_context=project_context,
            plan=user_plan,
        )

        logger.info(f"Cita formateada exitosamente con modelo {model_used}")

        return CitationResponse(
            citation=citation,
            model_used=model_used,
        )

    except HTTPException:
        # Re-raise HTTPException para que FastAPI las maneje correctamente
        raise

    except ModelNotAvailableError as e:
        logger.warning(
            f"Modelo no disponible para usuario {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "feature_not_available",
                "message": str(e),
                "details": {"feature": "citations", "plan": user_plan.value},
            },
        )

    except AIServiceError as e:
        logger.error(f"Error del servicio de IA: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ai_service_error",
                "message": "Error al formatear la cita. Por favor, intenta nuevamente.",
                "details": {"error_type": type(e).__name__},
            },
        )

    except Exception as e:
        logger.error(f"Error inesperado en formateo de citas: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Error interno del servidor",
                "details": {},
            },
        )


# =============================================================================
# ENDPOINT: BÚSQUEDA DE BIBLIOGRAFÍA
# =============================================================================


@project_router.post(
    "/proyectos/{project_id}/ia/bibliografias",
    response_model=BibliographyResponse,
    status_code=status.HTTP_200_OK,
    summary="Buscar fuentes bibliográficas relevantes",
    description="""
    Busca y sugiere fuentes bibliográficas académicas relevantes usando IA.

    Este endpoint utiliza el modelo Gemini con la capacidad de **Grounding**
    (Fundamentación con Búsqueda de Google) para encontrar fuentes académicas
    reales y verificables.

    **Funcionalidad**:
    - Busca artículos científicos, libros, tesis y documentos académicos
    - Prioriza fuentes confiables y actuales
    - Devuelve metadatos completos (autores, año, DOI, URL, etc.)
    - Incluye un score de relevancia (1-5)
    - Proporciona un resumen de por qué cada fuente es relevante

    **Nota**: Esta funcionalidad está disponible solo para planes
    Investigador y Profesional (no disponible en plan Estudiante).
    """,
    responses={
        200: {
            "description": "Búsqueda completada exitosamente",
            "model": BibliographyResponse,
        },
        401: {"description": "No autorizado - Token inválido o ausente"},
        403: {
            "description": "Sin acceso al proyecto o funcionalidad no disponible para tu plan",
            "model": AIErrorResponse,
        },
        404: {"description": "Proyecto no encontrado"},
        500: {
            "description": "Error interno del servidor o del servicio de IA",
            "model": AIErrorResponse,
        },
    },
)
async def search_bibliography(
    project_id: int,
    request: BibliographyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BibliographyResponse:
    """
    Busca fuentes bibliográficas académicas relevantes.

    Args:
        project_id: ID del proyecto
        request: Consulta de búsqueda y parámetros
        current_user: Usuario autenticado
        db: Sesión de base de datos

    Returns:
        BibliographyResponse: Lista de fuentes encontradas y modelo utilizado

    Raises:
        HTTPException: Si hay errores de autorización, proyecto no encontrado o del servicio de IA
    """
    try:
        logger.info(
            f"Usuario {current_user.email} busca bibliografía en proyecto {project_id}: '{request.query}'"
        )

        # Verificar que el proyecto existe y el usuario tiene acceso
        project = project_service.get_user_project_by_id(
            db,
            project_id=project_id,
            owner_id=current_user.id,  # type: ignore
        )
        if not project:
            logger.warning(f"Proyecto {project_id} no encontrado o usuario sin acceso")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto no encontrado o sin acceso",
            )

        # TODO: Determinar el plan del usuario desde la base de datos
        # Por ahora usamos plan investigador (tiene acceso a bibliografía)
        user_plan = UserPlan.INVESTIGADOR

        # Formatear contexto del proyecto si se proporciona en el request
        project_context_str = None
        if request.project_context:
            project_context_str = format_project_context(
                project_name=request.project_context.get("name", ""),
                description=request.project_context.get("description", ""),
                research_type=request.project_context.get("research_type", ""),
            )
        # Si no viene en el request, usar el del proyecto de la DB
        elif project:
            project_context_str = format_project_context(
                project_name=project.name,
                description=project.description or "",
                research_type=project.research_type or "",
            )

        # Llamar al servicio de IA
        sources, model_used = await ai_service.search_bibliography(
            query=request.query,
            max_results=request.max_results,
            plan=user_plan,
            project_context=project_context_str,
            search_context=request.search_context,
        )

        # Convertir sources a formato de schema
        bibliography_sources = []
        for source in sources:
            try:
                bibliography_sources.append(
                    {
                        "titulo": source.get("titulo", ""),
                        "autores": source.get("autores", []),
                        "anio": source.get("anio"),  # Puede ser None
                        "tipo": source.get("tipo", ""),
                        "fuente": source.get("fuente", ""),
                        "doi": source.get("doi"),
                        "url": source.get("url", ""),
                        "resumen": source.get("resumen", ""),
                        "relevancia": source.get("relevancia", 3),
                    }
                )
            except Exception as e:
                logger.warning(f"Error al procesar fuente: {str(e)}")
                continue

        logger.info(
            f"Búsqueda bibliográfica completada: {len(bibliography_sources)} fuentes encontradas"
        )

        return BibliographyResponse(
            sources=bibliography_sources,
            model_used=model_used,
            total_found=len(bibliography_sources),
        )

    except HTTPException:
        # Re-raise HTTPException para que FastAPI las maneje correctamente
        raise

    except ModelNotAvailableError as e:
        logger.warning(
            f"Modelo no disponible para usuario {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "feature_not_available",
                "message": "La búsqueda de bibliografía no está disponible en tu plan actual. Actualiza a plan Investigador o Profesional.",
                "details": {"feature": "bibliography", "plan": user_plan.value},
            },
        )

    except AIServiceError as e:
        logger.error(f"Error del servicio de IA: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ai_service_error",
                "message": "Error al buscar bibliografía. Por favor, intenta nuevamente.",
                "details": {"error_type": type(e).__name__},
            },
        )

    except Exception as e:
        logger.error(
            f"Error inesperado en búsqueda bibliográfica: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Error interno del servidor",
                "details": {},
            },
        )


# =============================================================================
# ENDPOINTS: CONVERSACIONES CON HISTORIAL PERSISTENTE
# =============================================================================


@project_router.get(
    "/proyectos/{project_id}/conversaciones",
    response_model=list[ConversationListResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar conversaciones de un proyecto",
    description="""
    Obtiene todas las conversaciones de chat del usuario en un proyecto específico.

    Las conversaciones se retornan ordenadas por última actualización (más recientes primero).
    Incluye un preview del último mensaje y el contador de mensajes.
    """,
)
async def list_conversations(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConversationListResponse]:
    """Lista todas las conversaciones del usuario en un proyecto."""
    try:
        # Verificar acceso al proyecto
        project = project_service.get_user_project_by_id(
            db, project_id=project_id, owner_id=current_user.id  # type: ignore
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto no encontrado o sin acceso",
            )

        # Obtener conversaciones
        conversations = conversation_repository.get_by_project_and_user(
            db, project_id=project_id, user_id=current_user.id  # type: ignore
        )

        # Construir respuesta con metadata
        response = []
        for conv in conversations:
            message_count = conversation_repository.get_message_count(db, conv.id)
            last_message = message_repository.get_last_message(db, conv.id)

            response.append(
                ConversationListResponse(
                    id=conv.id,
                    project_id=conv.project_id,
                    user_id=conv.user_id,
                    title=conv.title,
                    created_at=conv.created_at,
                    updated_at=conv.updated_at,
                    message_count=message_count,
                    last_message_preview=last_message.content[:100]
                    if last_message
                    else None,
                )
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listando conversaciones: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener conversaciones",
        )


@project_router.get(
    "/proyectos/{project_id}/conversaciones/{conversation_id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener una conversación con todos sus mensajes",
)
async def get_conversation(
    project_id: int,
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """Obtiene una conversación específica con todo su historial de mensajes."""
    try:
        # Verificar acceso al proyecto
        project = project_service.get_user_project_by_id(
            db, project_id=project_id, owner_id=current_user.id  # type: ignore
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto no encontrado o sin acceso",
            )

        # Obtener conversación con mensajes
        conversation = conversation_repository.get_with_messages(
            db, conversation_id=conversation_id, user_id=current_user.id  # type: ignore
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversación no encontrada",
            )

        return ConversationResponse.model_validate(conversation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo conversación: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener conversación",
        )


@project_router.patch(
    "/proyectos/{project_id}/conversaciones/{conversation_id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar título de conversación",
)
async def update_conversation(
    project_id: int,
    conversation_id: int,
    data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """Actualiza el título de una conversación."""
    try:
        if not data.title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El título no puede estar vacío",
            )

        # Verificar acceso al proyecto
        project = project_service.get_user_project_by_id(
            db, project_id=project_id, owner_id=current_user.id  # type: ignore
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto no encontrado o sin acceso",
            )

        # Actualizar conversación
        conversation = conversation_repository.update_title(
            db, conversation_id=conversation_id, user_id=current_user.id, new_title=data.title  # type: ignore
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversación no encontrada",
            )

        # Recargar con mensajes
        conversation = conversation_repository.get_with_messages(
            db, conversation_id=conversation_id, user_id=current_user.id  # type: ignore
        )

        return ConversationResponse.model_validate(conversation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando conversación: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar conversación",
        )


@project_router.delete(
    "/proyectos/{project_id}/conversaciones/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una conversación",
)
async def delete_conversation(
    project_id: int,
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Elimina una conversación y todos sus mensajes."""
    try:
        # Verificar acceso al proyecto
        project = project_service.get_user_project_by_id(
            db, project_id=project_id, owner_id=current_user.id  # type: ignore
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto no encontrado o sin acceso",
            )

        # Eliminar conversación
        deleted = conversation_repository.delete(db, id=conversation_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversación no encontrada",
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando conversación: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar conversación",
        )


@project_router.post(
    "/proyectos/{project_id}/chat",
    response_model=ChatWithHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat con historial persistente",
    description="""
    Envía un mensaje al asistente IA y guarda el historial en la base de datos.

    - Si se proporciona `conversation_id`, continúa la conversación existente.
    - Si NO se proporciona, crea una nueva conversación automáticamente.
    - El historial completo se guarda en la base de datos.
    - Retorna la respuesta del asistente y el ID de la conversación.
    """,
)
async def chat_with_persistent_history(
    project_id: int,
    request: ChatWithHistoryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatWithHistoryResponse:
    """
    Chat con el asistente IA con historial persistente.
    """
    try:
        logger.info(
            f"Usuario {current_user.email} envía mensaje en proyecto {project_id}"
        )

        # Verificar acceso al proyecto
        project = project_service.get_user_project_by_id(
            db, project_id=project_id, owner_id=current_user.id  # type: ignore
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto no encontrado o sin acceso",
            )

        # Obtener o crear conversación
        if request.conversation_id:
            # Continuar conversación existente
            conversation = conversation_repository.get_with_messages(
                db, conversation_id=request.conversation_id, user_id=current_user.id  # type: ignore
            )
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversación no encontrada",
                )
        else:
            # Crear nueva conversación
            title = request.title or "Nueva conversación"
            conversation = conversation_repository.create_conversation(
                db, project_id=project_id, user_id=current_user.id, title=title  # type: ignore
            )

        # Guardar mensaje del usuario
        user_message = message_repository.create_message(
            db,
            conversation_id=conversation.id,
            role="user",
            content=request.message,
        )

        # Construir historial para el servicio de IA
        history_for_ai = [
            {"role": msg.role, "content": msg.content}
            for msg in conversation.messages
            if msg.id != user_message.id  # Excluir el mensaje recién creado
        ]

        # Obtener contenido del documento adjunto
        document_content = None
        try:
            attachment = attachment_service.get_attachment_by_parent(
                db, parent_type="project", parent_id=project_id, user_id=current_user.id
            )
            if (
                attachment
                and attachment.file_path
                and str(attachment.file_path).endswith(".docx")
            ):
                # Extraer contenido del documento (primeros 10000 caracteres para contexto)
                document_content = document_extraction_service.get_document_preview(
                    str(attachment.file_path), max_chars=10000
                )
        except Exception as e:
            logger.warning(f"Error al obtener contenido del documento para chat: {e}")

        # Obtener bibliografías del proyecto
        bibliographies_summary = None
        try:
            bibliographies = bibliography_repository.get_by_project(
                db, project_id=project_id
            )
            if bibliographies:
                # Convertir a lista de dicts para el formateador
                bib_list = [
                    {
                        "autores": b.author,
                        "anio": b.year,
                        "titulo": b.title,
                        "tipo": b.type,
                    }
                    for b in bibliographies
                ]
                bibliographies_summary = format_bibliography_context(bib_list)
        except Exception as e:
            logger.warning(f"Error al obtener bibliografías para chat: {e}")

        # Formatear contexto del proyecto
        project_context = format_project_context(
            project_name=project.name,  # type: ignore
            description=project.description,  # type: ignore
            research_type=project.research_type,  # type: ignore
            documents_summary=document_content,
            bibliographies_summary=bibliographies_summary,
        )

        # Llamar al servicio de IA
        user_plan = UserPlan.PROFESIONAL  # TODO: Obtener del usuario
        response_text, model_used = await ai_service.chat(
            message=request.message,
            history=history_for_ai,
            project_context=project_context,
            plan=user_plan,
        )

        # Guardar respuesta del asistente
        assistant_message = message_repository.create_message(
            db,
            conversation_id=conversation.id,
            role="model",
            content=response_text,
            model_used=model_used,
        )

        logger.info(
            f"Chat completado: conversación {conversation.id}, modelo {model_used}"
        )

        return ChatWithHistoryResponse(
            response=response_text,
            model_used=model_used,
            conversation_id=conversation.id,
            message_id=assistant_message.id,
        )

    except HTTPException:
        raise
    except ModelNotAvailableError as e:
        logger.warning(f"Modelo no disponible: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "feature_not_available",
                "message": str(e),
                "details": {"feature": "chat"},
            },
        )
    except AIServiceError as e:
        logger.error(f"Error del servicio de IA: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ai_service_error",
                "message": "Error al generar respuesta. Intenta nuevamente.",
                "details": {"error_type": type(e).__name__},
            },
        )
    except Exception as e:
        logger.error(f"Error inesperado en chat: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Error interno del servidor",
                "details": {},
            },
        )
