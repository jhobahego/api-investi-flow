from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.attachment import AttachmentResponse
from app.schemas.phase import PhaseCreate, PhaseListResponse, PhaseOrder, PhaseUpdate
from app.services.attachment_service import attachment_service
from app.services.phase_service import phase_service

router = APIRouter()


@router.post("/", response_model=PhaseListResponse, status_code=status.HTTP_201_CREATED)
async def create_phase(
    *,
    db: Session = Depends(get_db),
    phase_in: PhaseCreate,
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id
    return phase_service.create_phase(
        db=db,
        phase_in=phase_in,
        owner_id=user_id,  # type: ignore
    )


@router.post("/{phase_id}/documentos", status_code=status.HTTP_201_CREATED)
async def upload_document(
    *,
    db: Session = Depends(get_db),
    phase_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> AttachmentResponse:
    """
    Subir un nuevo documento a la fase.

    Solo el propietario del proyecto al que pertenece la fase puede subir documentos.
    """
    try:
        document = attachment_service.create_attachment(
            db=db,
            file=file,
            parent_type="phase",
            parent_id=phase_id,
            user_id=current_user.id,  # type: ignore
        )

        return AttachmentResponse.model_validate(document)

    except Exception:
        raise


@router.get("/{phase_id}/documentos")
async def get_phase_document(
    *,
    db: Session = Depends(get_db),
    phase_id: int,
    current_user: User = Depends(get_current_user),
) -> Optional[AttachmentResponse]:
    """
    Obtener el documento adjunto de la fase.

    Solo el propietario del proyecto al que pertenece la fase puede acceder al documento.
    Retorna None si no hay documento adjunto.
    """
    try:
        attachment = attachment_service.get_attachment_by_parent(
            db=db,
            parent_type="phase",
            parent_id=phase_id,
            user_id=current_user.id,  # type: ignore
        )

        if attachment:
            return AttachmentResponse.model_validate(attachment)
        return None

    except Exception:
        raise


@router.get("/{phase_id}", response_model=PhaseListResponse)
async def get_phase_by_id(
    *,
    db: Session = Depends(get_db),
    phase_id: int,
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id
    return phase_service.get_phase_by_id(
        db=db,
        phase_id=phase_id,
        owner_id=user_id,  # type: ignore
    )


@router.get("/{phase_id}/tareas")
async def get_phase_tasks(
    *,
    db: Session = Depends(get_db),
    phase_id: int,
    current_user: User = Depends(get_current_user),
):
    return phase_service.get_phase_tasks(
        db=db,
        phase_id=phase_id,
    )


@router.put("/{phase_id}", response_model=PhaseListResponse)
async def update_phase(
    *,
    db: Session = Depends(get_db),
    phase_id: int,
    phase_in: PhaseUpdate,
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id
    return phase_service.update_phase(
        db=db,
        phase_id=phase_id,
        phase_in=phase_in,
        owner_id=user_id,  # type: ignore
    )


@router.delete("/{phase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_phase(
    *,
    db: Session = Depends(get_db),
    phase_id: int,
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id
    phase_service.delete_phase(
        db=db,
        phase_id=phase_id,
        owner_id=user_id,  # type: ignore
    )


@router.put("/project/{project_id}/reorder", response_model=List[PhaseListResponse])
async def reorder_project_phases(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    phase_orders: List[PhaseOrder],
    current_user: User = Depends(get_current_user),
):
    """
    Reordena las fases de un proyecto.
    """
    user_id = current_user.id
    phase_orders_dict = [order.model_dump() for order in phase_orders]
    return phase_service.reorder_phases(
        db=db,
        project_id=project_id,
        phase_orders=phase_orders_dict,
        owner_id=user_id,  # type: ignore
    )
