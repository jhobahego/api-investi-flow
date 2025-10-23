import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.ai_config import UserPlan
from app.core.ai_prompts import format_project_context
from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.ai import (
    AIErrorResponse,
    BibliographyRequest,
    BibliographyResponse,
    ChatRequest,
    ChatResponse,
    CitationRequest,
    CitationResponse,
    SuggestionRequest,
    SuggestionResponse,
)
from app.services.ai_service import AIServiceError, ModelNotAvailableError, ai_service
from app.services.project_service import project_service

logger = logging.getLogger(__name__)

router = APIRouter()


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
# ENDPOINT: CHAT CONTEXTUAL
# =============================================================================


@router.post(
    "/proyectos/{project_id}/ia/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat con asistente IA contextual al proyecto",
    description="""
    Inicia o continúa una conversación con el asistente de IA en el contexto de un proyecto.

    El asistente tiene acceso a:
    - Información del proyecto (nombre, descripción, tipo de investigación, objetivos)
    - Historial de la conversación
    - Documentos adjuntos al proyecto (en desarrollo)
    - Bibliografía del proyecto (en desarrollo)

    El modelo utilizado depende del plan del usuario:
    - Plan Estudiante: gemini-2.0-flash-exp
    - Plan Investigador: gemini-2.0-flash-exp
    - Plan Profesional: gemini-2.0-flash-thinking-exp (más potente)

    **Nota**: Por ahora usa el plan Profesional con el modelo más potente.
    """,
    responses={
        200: {
            "description": "Respuesta del asistente generada exitosamente",
            "model": ChatResponse,
        },
        401: {"description": "No autorizado - Token inválido o ausente"},
        403: {"description": "Sin acceso al proyecto o funcionalidad no disponible"},
        404: {"description": "Proyecto no encontrado"},
        500: {
            "description": "Error interno del servidor o del servicio de IA",
            "model": AIErrorResponse,
        },
    },
)
async def chat_with_ai(
    project_id: int,
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    """
    Conversación con el asistente de IA en el contexto de un proyecto.

    Args:
        project_id: ID del proyecto
        request: Mensaje y historial del chat
        current_user: Usuario autenticado
        db: Sesión de base de datos

    Returns:
        ChatResponse: Respuesta del asistente y modelo utilizado

    Raises:
        HTTPException: Si hay errores de autorización, proyecto no encontrado o del servicio de IA
    """
    try:
        logger.info(
            f"Usuario {current_user.email} inicia chat en proyecto {project_id}"
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
        # Por ahora usamos el plan profesional (modelo más potente) para chat
        user_plan = UserPlan.PROFESIONAL

        # Formatear contexto del proyecto
        project_context = format_project_context(
            project_name=project.name,  # type: ignore
            description=project.description,  # type: ignore
            research_type=project.research_type,  # type: ignore
            # TODO: Agregar resumen de documentos adjuntos
        )

        # Convertir historial al formato esperado por el servicio
        history_dict = [msg.model_dump() for msg in request.history]

        # Llamar al servicio de IA
        response_text, model_used = await ai_service.chat(
            message=request.message,
            history=history_dict,
            project_context=project_context,
            plan=user_plan,
        )

        logger.info(f"Respuesta de chat generada exitosamente con modelo {model_used}")

        return ChatResponse(
            response=response_text,
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
                "details": {"feature": "chat", "plan": user_plan.value},
            },
        )

    except AIServiceError as e:
        logger.error(f"Error del servicio de IA: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ai_service_error",
                "message": "Error al generar la respuesta del chat. Por favor, intenta nuevamente.",
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


# =============================================================================
# ENDPOINT: FORMATEO DE CITAS APA 7
# =============================================================================


@router.post(
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


@router.post(
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

        # Llamar al servicio de IA
        sources, model_used = await ai_service.search_bibliography(
            query=request.query,
            max_results=request.max_results,
            plan=user_plan,
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
