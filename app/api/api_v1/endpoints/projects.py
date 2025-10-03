from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.attachment import AttachmentResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.attachment_service import attachment_service
from app.services.project_service import project_service

router = APIRouter()


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    *,
    db: Session = Depends(get_db),
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    """
    Crear un nuevo proyecto.

    - **name**: Nombre del proyecto (requerido)
    - **description**: Descripción del proyecto (opcional)
    - **research_type**: Tipo de investigación (opcional)
    - **institution**: Institución (opcional)
    - **research_group**: Grupo de investigación (opcional)
    - **category**: Categoría del proyecto (opcional)
    - **status**: Estado del proyecto (opcional, por defecto: planning)
    """
    try:
        project = project_service.create_project(
            db=db,
            project_in=project_in,
            owner_id=current_user.id,  # type: ignore
        )
        return project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}",
        )


@router.post("/{project_id}/documentos", status_code=status.HTTP_201_CREATED)
async def upload_document(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> AttachmentResponse:
    """
    Subir un nuevo documento al proyecto.

    Solo el propietario del proyecto puede subir documentos.
    """
    try:
        document = attachment_service.create_attachment(
            db=db,
            file=file,
            parent_type="project",
            parent_id=project_id,
            user_id=current_user.id,  # type: ignore
        )

        return AttachmentResponse.model_validate(document)

    except Exception:
        raise


@router.get("/", response_model=List[ProjectListResponse])
def list_projects(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Listar todos los proyectos del usuario autenticado.

    Retorna una lista con todos los proyectos creados por el usuario actual,
    ordenados por fecha de creación (más recientes primero).
    """
    try:
        projects = project_service.get_user_projects(db=db, owner_id=current_user.id)  # type: ignore
        return projects
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}",
        )


@router.get("/search", response_model=List[ProjectListResponse])
async def list_user_projects_by_search(
    *,
    db: Session = Depends(get_db),
    query: Optional[str] = None,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Listar todos los proyectos del usuario autenticado que coincidan con la búsqueda.

    Retorna una lista con todos los proyectos creados por el usuario actual,
    cuyo nombre contenga la subcadena de búsqueda, ordenados por fecha de creación (más recientes primero).
    Si no se proporciona una cadena de búsqueda, se retornan todos los proyectos del usuario.
    """
    return project_service.search_user_projects_by_name(
        db=db,
        query=query,  # type: ignore
        owner_id=current_user.id,  # type: ignore
    )


@router.get("/{project_id}/documentos")
async def get_project_document(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    current_user: User = Depends(get_current_user),
) -> Optional[AttachmentResponse]:
    """
    Obtener el documento adjunto del proyecto.

    Solo el propietario del proyecto puede acceder al documento.
    Retorna None si no hay documento adjunto.
    """
    try:
        attachment = attachment_service.get_attachment_by_parent(
            db=db,
            parent_type="project",
            parent_id=project_id,
            user_id=current_user.id,  # type: ignore
        )

        if attachment:
            return AttachmentResponse.model_validate(attachment)
        return None

    except Exception:
        raise


@router.get("/{project_id}/phases")
async def get_project_with_phases(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    current_user: User = Depends(get_current_user),
):
    try:
        return project_service.get_project_with_phases(
            db=db,
            project_id=project_id,
            owner_id=current_user.id,  # type: ignore
        )

    except HTTPException:
        raise

    except Exception:
        raise


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    """
    Obtener los detalles de un proyecto específico.

    Solo el propietario del proyecto puede acceder a sus detalles.
    """
    try:
        project = project_service.get_user_project_by_id(
            db=db,
            project_id=project_id,
            owner_id=current_user.id,  # type: ignore
        )
        return project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}",
        )


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    project_in: ProjectUpdate,
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    """
    Actualizar un proyecto existente.

    Solo el propietario del proyecto puede actualizarlo.
    Todos los campos son opcionales, solo se actualizarán los campos proporcionados.
    """
    try:
        project = project_service.update_user_project(
            db=db,
            project_id=project_id,
            project_in=project_in,
            owner_id=current_user.id,  # type: ignore
        )
        return project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}",
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Eliminar un proyecto.

    Solo el propietario del proyecto puede eliminarlo.
    Esta acción es irreversible y eliminará también todos los documentos,
    tareas y bibliografías asociadas al proyecto.
    """
    try:
        project_service.delete_user_project(
            db=db,
            project_id=project_id,
            owner_id=current_user.id,  # type: ignore
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}",
        )


@router.get("/{project_id}/descargar-documento")
async def download_project_document(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """
    Descargar el documento adjunto del proyecto.

    Solo el propietario del proyecto puede descargar el documento.
    El archivo se descargará con su nombre original y el navegador
    iniciará automáticamente la descarga.

    Returns:
        FileResponse: Archivo para descargar

    Raises:
        HTTPException 404: Si el proyecto no existe o no tiene documento adjunto
        HTTPException 403: Si el usuario no tiene permisos
        HTTPException 500: Si hay un error al acceder al archivo
    """
    try:
        # Obtener el documento adjunto del proyecto
        attachment = attachment_service.get_attachment_by_parent(
            db=db,
            parent_type="project",
            parent_id=project_id,
            user_id=current_user.id,  # type: ignore
        )

        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El proyecto no tiene un documento adjunto",
            )

        # Verificar que el archivo existe en el sistema de archivos
        file_path = Path(str(attachment.file_path))
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El archivo no se encuentra en el sistema",
            )

        # Determinar el tipo MIME según la extensión del archivo
        media_type_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
        }

        file_extension = file_path.suffix.lower()
        media_type = media_type_map.get(file_extension, "application/octet-stream")

        # Obtener el nombre del archivo como string
        filename = str(attachment.file_name)

        # Encodear el nombre del archivo para el header según RFC 5987
        # Esto maneja correctamente caracteres especiales (acentos, ñ, etc.)
        filename_encoded = quote(filename)

        # Crear el header Content-Disposition con ambos formatos para máxima compatibilidad
        # filename* es el estándar RFC 5987 para caracteres no-ASCII
        content_disposition = (
            f"attachment; "
            f'filename="{filename.encode("ascii", "ignore").decode("ascii")}"; '
            f"filename*=UTF-8''{filename_encoded}"
        )

        # Retornar el archivo para descarga
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type=media_type,
            headers={"Content-Disposition": content_disposition},
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error al descargar el documento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al descargar el documento",
        )
