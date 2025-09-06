from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas import TaskCreate, TaskResponse, TaskUpdate
from app.services import task_service

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
