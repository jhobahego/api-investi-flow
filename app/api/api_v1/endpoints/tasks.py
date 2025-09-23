from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.attachment import AttachmentResponse
from app.schemas.task import TaskCreate, TaskDataToMovePhase, TaskResponse, TaskUpdate
from app.services import task_service
from app.services.attachment_service import attachment_service

router = APIRouter()


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    *,
    db: Session = Depends(get_db),
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
):
    """
    Crea una nueva tarea para el usuario autenticado.

    Args:
        db (Session): Sesión de base de datos proporcionada por la dependencia.
        task_in (TaskCreate): Datos requeridos para crear una nueva tarea.
        current_user (User): El usuario actualmente autenticado.

    Returns:
        TaskResponse: Los datos de la tarea creada.
    """
    user_id = current_user.id
    return task_service.create_task(
        db=db,
        task_in=task_in,
        owner_id=user_id,  # type: ignore
    )


@router.post("/{task_id}/documentos", status_code=status.HTTP_201_CREATED)
async def upload_document(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> AttachmentResponse:
    """
    Subir un nuevo documento a la tarea.

    Solo el propietario del proyecto al que pertenece la tarea puede subir documentos.
    """
    try:
        document = attachment_service.create_attachment(
            db=db,
            file=file,
            parent_type="task",
            parent_id=task_id,
            user_id=current_user.id,  # type: ignore
        )

        return AttachmentResponse.model_validate(document)

    except Exception:
        raise


@router.get("/{task_id}/documentos")
async def get_task_document(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    current_user: User = Depends(get_current_user),
) -> Optional[AttachmentResponse]:
    """
    Obtener el documento adjunto de la tarea.

    Solo el propietario del proyecto al que pertenece la tarea puede acceder al documento.
    Retorna None si no hay documento adjunto.
    """
    try:
        attachment = attachment_service.get_attachment_by_parent(
            db=db,
            parent_type="task",
            parent_id=task_id,
            user_id=current_user.id,  # type: ignore
        )

        if attachment:
            return AttachmentResponse.model_validate(attachment)
        return None

    except Exception:
        raise


@router.get("/", response_model=list[TaskResponse])
async def get_tasks_by_phase(
    *,
    db: Session = Depends(get_db),
    phase_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene todas las tareas asociadas a una fase específica para el usuario autenticado.

    Args:
        db (Session): Sesión de base de datos proporcionada por la dependencia.
        phase_id (int): ID de la fase para la cual se desean obtener las tareas.
        current_user (User): El usuario actualmente autenticado.

    Returns:
        list[TaskResponse]: Una lista de tareas asociadas a la fase especificada.
    """
    user_id = current_user.id
    return task_service.get_phase_tasks(
        db=db,
        phase_id=phase_id,
        owner_id=user_id,  # type: ignore
    )


@router.put("/{task_id}/mover")
async def move_task_to_phase(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    data_to_update: TaskDataToMovePhase,
    current_user: User = Depends(get_current_user),
):
    """
    Mueve una tarea a una nueva fase y posición dentro de esa fase.

    Args:
        db (Session): Sesión de base de datos proporcionada por la dependencia.
        task_id (int): ID de la tarea que se desea mover.
        data_to_update (TaskDataToMovePhase): Objeto que contiene los datos para mover la tarea, incluyendo:
            - new_phase_id (int): ID de la nueva fase a la que se moverá la tarea.
            - new_position (Optional[int]): Posición en la que se va a ubicar en la nueva fase (opcional).
        current_user (User): El usuario actualmente autenticado.

    Returns:
        TaskResponse: Los datos de la tarea movida.
    """
    user_id = current_user.id
    new_phase_id = data_to_update.new_phase_id
    new_position = data_to_update.new_position
    return task_service.move_task_to_phase(
        db=db,
        task_id=task_id,
        new_phase_id=new_phase_id,
        new_position=new_position,
        owner_id=user_id,  # type: ignore
    )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_user),
):
    """
    Actualiza una tarea existente para el usuario autenticado.

    Args:
        db (Session): Sesión de base de datos proporcionada por la dependencia.
        task_id (int): ID de la tarea que se desea actualizar.
        task_in (TaskUpdate): Datos para actualizar la tarea.
        current_user (User): El usuario actualmente autenticado.
    Returns:
        TaskResponse: Los datos de la tarea actualizada.
    """
    user_id = current_user.id
    return task_service.update_task(
        db=db,
        task_id=task_id,
        task_in=task_in,
        owner_id=user_id,  # type: ignore
    )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    Elimina una tarea existente para el usuario autenticado.

    Args:
        db (Session): Sesión de base de datos proporcionada por la dependencia.
        task_id (int): ID de la tarea que se desea eliminar.
        current_user (User): El usuario actualmente autenticado.

    Returns:
        None
    """
    user_id = current_user.id
    return task_service.delete_task(
        db=db,
        task_id=task_id,
        owner_id=user_id,  # type: ignore
    )
