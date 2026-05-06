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
from app.repositories.phase_repository import phase_repository
from app.repositories.task_repository import task_repository
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
            db,
            project_id=project_id,
            owner_id=current_user.id,  # type: ignore
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto no encontrado o sin acceso",
            )

        # Obtener conversaciones
        conversations = conversation_repository.get_by_project_and_user(
            db,
            project_id=project_id,
            user_id=current_user.id,  # type: ignore
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
            db,
            project_id=project_id,
            owner_id=current_user.id,  # type: ignore
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto no encontrado o sin acceso",
            )

        # Obtener conversación con mensajes
        conversation = conversation_repository.get_with_messages(
            db,
            conversation_id=conversation_id,
            user_id=current_user.id,  # type: ignore
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
            db,
            project_id=project_id,
            owner_id=current_user.id,  # type: ignore
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto no encontrado o sin acceso",
            )

        # Actualizar conversación
        conversation = conversation_repository.update_title(
            db,
            conversation_id=conversation_id,
            user_id=current_user.id,
            new_title=data.title,  # type: ignore
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversación no encontrada",
            )

        # Recargar con mensajes
        conversation = conversation_repository.get_with_messages(
            db,
            conversation_id=conversation_id,
            user_id=current_user.id,  # type: ignore
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
            db,
            project_id=project_id,
            owner_id=current_user.id,  # type: ignore
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
async def chat_with_persistent_history(  # noqa: C901
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
            db,
            project_id=project_id,
            owner_id=current_user.id,  # type: ignore
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
                db,
                conversation_id=request.conversation_id,
                user_id=current_user.id,  # type: ignore
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
                db,
                project_id=project_id,
                user_id=current_user.id,
                title=title,  # type: ignore
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

        # Variables para summaries
        documents_contents = []
        bibliographies_summary = None
        fases_summary = None
        tareas_summary = None

        if request.project_context:
            ctx = request.project_context

            # 1. Extraer Documentos Principales del Proyecto
            if ctx.attachment_document:
                for doc in ctx.attachment_document:
                    if (
                        isinstance(doc, dict)
                        and doc.get("file_path")
                        and str(doc["file_path"]).endswith((".docx", ".pdf"))
                    ):
                        try:
                            content = document_extraction_service.get_document_preview(
                                str(doc["file_path"]), max_chars=50000
                            )
                            documents_contents.append(
                                f"Documento Base ({doc.get('file_name', 'Adjunto')}):\n{content}"
                            )
                        except Exception as e:
                            logger.warning(f"Error extrayendo {doc['file_path']}: {e}")

            # 2. Extraer Fases, Tareas y Documentos Asociados
            if ctx.fases:
                fases_list = []
                tareas_list = []
                for i, phase in enumerate(ctx.fases):
                    if not isinstance(phase, dict):
                        continue

                    phase_name = (
                        phase.get("nombre") or phase.get("name") or f"Fase {i + 1}"
                    )
                    fases_list.append(f"{i + 1}. {phase_name}")

                    # Documento de la fase
                    p_doc = phase.get("attachment_document")
                    if (
                        p_doc
                        and isinstance(p_doc, dict)
                        and p_doc.get("file_path")
                        and str(p_doc["file_path"]).endswith((".docx", ".pdf"))
                    ):
                        try:
                            content = document_extraction_service.get_document_preview(
                                str(p_doc["file_path"]), max_chars=25000
                            )
                            documents_contents.append(
                                f"Documento de Fase '{phase_name}' ({p_doc.get('file_name', 'Adjunto')}):\n{content}"
                            )
                        except Exception as e:
                            logger.warning(f"Error extrayendo doc de fase: {e}")

                    # Tareas de la fase
                    tasks = phase.get("tareas")
                    if isinstance(tasks, list):
                        for t in tasks:
                            if not isinstance(t, dict):
                                continue
                            task_name = t.get("title") or t.get("name") or "Tarea"
                            task_status = t.get("status", "pendiente")
                            tareas_list.append(
                                f"- Fase '{phase_name}': {task_name} ({task_status})"
                            )

                            # Documento de la tarea
                            t_doc = t.get("attachment_document")
                            if (
                                t_doc
                                and isinstance(t_doc, dict)
                                and t_doc.get("file_path")
                                and str(t_doc["file_path"]).endswith((".docx", ".pdf"))
                            ):
                                try:
                                    content = document_extraction_service.get_document_preview(
                                        str(t_doc["file_path"]), max_chars=15000
                                    )
                                    documents_contents.append(
                                        f"Documento de Tarea '{task_name}' ({t_doc.get('file_name', 'Adjunto')}):\n{content}"
                                    )
                                except Exception as e:
                                    logger.warning(
                                        f"Error extrayendo doc de tarea: {e}"
                                    )

                if fases_list:
                    fases_summary = "\n".join(fases_list)
                if tareas_list:
                    tareas_summary = "\n".join(tareas_list)

            # 3. Bibliografía
            if ctx.bibliografia:
                try:
                    bib_list = [
                        {
                            "autores": b.get("author")
                            or b.get("autores")
                            or b.get("autor"),
                            "anio": b.get("year") or b.get("anio"),
                            "titulo": b.get("title") or b.get("titulo"),
                            "tipo": b.get("type") or b.get("tipo", "documento"),
                        }
                        for b in ctx.bibliografia
                        if isinstance(b, dict)
                    ]
                    bibliographies_summary = format_bibliography_context(bib_list)
                except Exception as e:
                    logger.warning(f"Error al formatear bibliografía del request: {e}")

        # 4. Fallbacks a la Base de Datos si no vienen datos en el contexto
        if not fases_summary and project_id:
            try:
                db_phases = phase_repository.get_phases_by_project(
                    db, project_id=project_id
                )
                if db_phases:
                    fases_list = []
                    tareas_list = []
                    for i, phase in enumerate(db_phases):
                        phase_name = phase.name or f"Fase {i + 1}"
                        fases_list.append(f"{i + 1}. {phase_name}")

                        # Phase document
                        p_attach = attachment_service.get_attachment_by_parent(
                            db,
                            parent_type="phase",
                            parent_id=phase.id,
                            user_id=current_user.id,
                        )
                        if (
                            p_attach
                            and p_attach.file_path
                            and str(p_attach.file_path).endswith((".docx", ".pdf"))
                        ):
                            try:
                                content = (
                                    document_extraction_service.get_document_preview(
                                        str(p_attach.file_path), max_chars=25000
                                    )
                                )
                                documents_contents.append(
                                    f"Documento de Fase '{phase_name}' ({p_attach.file_name}):\n{content}"
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Error extrayendo doc de fase desde DB: {e}"
                                )

                        # Tasks
                        db_tasks = task_repository.get_tasks_by_phase(
                            db, phase_id=phase.id
                        )
                        if db_tasks:
                            for t in db_tasks:
                                task_name = t.title or "Tarea"
                                task_status = getattr(t, "status", "pendiente")
                                tareas_list.append(
                                    f"- Fase '{phase_name}': {task_name} ({task_status})"
                                )

                                # Task document
                                t_attach = attachment_service.get_attachment_by_parent(
                                    db,
                                    parent_type="task",
                                    parent_id=t.id,
                                    user_id=current_user.id,
                                )
                                if (
                                    t_attach
                                    and t_attach.file_path
                                    and str(t_attach.file_path).endswith(
                                        (".docx", ".pdf")
                                    )
                                ):
                                    try:
                                        content = document_extraction_service.get_document_preview(
                                            str(t_attach.file_path), max_chars=15000
                                        )
                                        documents_contents.append(
                                            f"Documento de Tarea '{task_name}' ({t_attach.file_name}):\n{content}"
                                        )
                                    except Exception as e:
                                        logger.warning(
                                            f"Error extrayendo doc de tarea desde DB: {e}"
                                        )

                    if fases_list:
                        fases_summary = "\n".join(fases_list)
                    if tareas_list:
                        tareas_summary = "\n".join(tareas_list)
            except Exception as e:
                logger.warning(f"Error recuperando fases y tareas desde DB: {e}")

        if not documents_contents:
            try:
                attachment = attachment_service.get_attachment_by_parent(
                    db,
                    parent_type="project",
                    parent_id=project_id,
                    user_id=current_user.id,
                )
                if (
                    attachment
                    and attachment.file_path
                    and str(attachment.file_path).endswith((".docx", ".pdf"))
                ):
                    content = document_extraction_service.get_document_preview(
                        str(attachment.file_path), max_chars=50000
                    )
                    documents_contents.append(f"Documento Base Principal:\n{content}")
            except Exception as e:
                logger.warning(
                    f"Error al obtener contenido del documento para chat: {e}"
                )

        document_content_summary = (
            "\n\n".join(documents_contents) if documents_contents else None
        )

        if not bibliographies_summary:
            try:
                bibliographies = bibliography_repository.get_by_project(
                    db, project_id=project_id
                )
                if bibliographies:
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
            documents_summary=document_content_summary,
            bibliographies_summary=bibliographies_summary,
            fases_summary=fases_summary,
            tareas_summary=tareas_summary,
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

        # Generar título para conversaciones nuevas si no se proporcionó uno
        if not request.conversation_id and not request.title:
            try:
                new_title = ai_service.generate_conversation_title(
                    message=request.message, response=response_text
                )
                if new_title:
                    conversation_repository.update_title(
                        db,
                        conversation_id=conversation.id,
                        title=new_title,
                        user_id=current_user.id,  # type: ignore
                    )
            except Exception as e:
                logger.warning(
                    f"Error al generar/actualizar título de conversación: {e}"
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
