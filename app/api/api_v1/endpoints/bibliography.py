import os
import shutil
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.repositories.bibliography_repository import bibliography_repository
from app.schemas.bibliography import (
    Bibliography,
    BibliographyCreate,
    BibliographyUpdate,
)
from app.services.project_service import project_service

router = APIRouter()

UPLOAD_DIR = "uploads/bibliographies"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def verify_project_access(project_id: int, current_user: User, db: Session):
    """Verifica que el proyecto exista y el usuario tenga acceso."""
    project = project_service.get_user_project_by_id(
        db=db,
        project_id=project_id,
        owner_id=current_user.id,  # type: ignore
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o sin acceso",
        )
    return project


@router.get(
    "/proyectos/{project_id}/bibliografias",
    response_model=List[Bibliography],
    summary="Listar bibliografías de un proyecto",
)
async def list_bibliographies(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene todas las referencias bibliográficas de un proyecto."""
    # Verificar acceso al proyecto
    await verify_project_access(project_id, current_user, db)

    return bibliography_repository.get_by_project(db, project_id=project_id)


@router.post(
    "/proyectos/{project_id}/bibliografias",
    response_model=Bibliography,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva referencia bibliográfica",
)
async def create_bibliography(
    project_id: int,
    bibliography_in: BibliographyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crea una nueva referencia bibliográfica en el proyecto."""
    # Verificar acceso al proyecto
    await verify_project_access(project_id, current_user, db)

    return bibliography_repository.create(
        db, project_id=project_id, obj_in=bibliography_in
    )


@router.put(
    "/proyectos/{project_id}/bibliografias/{bibliography_id}",
    response_model=Bibliography,
    summary="Actualizar referencia bibliográfica",
)
async def update_bibliography(
    project_id: int,
    bibliography_id: int,
    bibliography_in: BibliographyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Actualiza una referencia bibliográfica existente."""
    # Verificar acceso al proyecto
    await verify_project_access(project_id, current_user, db)

    bibliography = bibliography_repository.get_by_id(db, bibliography_id)
    if not bibliography:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bibliografía no encontrada"
        )

    if bibliography.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La bibliografía no pertenece a este proyecto",
        )

    return bibliography_repository.update(
        db, db_obj=bibliography, obj_in=bibliography_in
    )


@router.delete(
    "/proyectos/{project_id}/bibliografias/{bibliography_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar referencia bibliográfica",
)
async def delete_bibliography(
    project_id: int,
    bibliography_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Elimina una referencia bibliográfica."""
    # Verificar acceso al proyecto
    await verify_project_access(project_id, current_user, db)

    bibliography = bibliography_repository.get_by_id(db, bibliography_id)
    if not bibliography:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bibliografía no encontrada"
        )

    if bibliography.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La bibliografía no pertenece a este proyecto",
        )

    bibliography_repository.delete(db, bibliography_id)
    return None


@router.post(
    "/proyectos/{project_id}/bibliografias/{bibliography_id}/upload",
    response_model=Bibliography,
    summary="Subir documento asociado a bibliografía",
)
async def upload_bibliography_document(
    project_id: int,
    bibliography_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sube un documento (PDF, DOCX) asociado a una referencia bibliográfica."""
    # Verificar acceso al proyecto
    await verify_project_access(project_id, current_user, db)

    bibliography = bibliography_repository.get_by_id(db, bibliography_id)
    if not bibliography:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bibliografía no encontrada"
        )

    if bibliography.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La bibliografía no pertenece a este proyecto",
        )

    # Validar tipo de archivo
    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten archivos PDF y DOCX",
        )

    # Guardar archivo
    file_ext = os.path.splitext(file.filename)[1]
    file_path = os.path.join(UPLOAD_DIR, f"{project_id}_{bibliography_id}{file_ext}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return bibliography_repository.update_file(
        db, bibliography_id, file_path, file.filename
    )
