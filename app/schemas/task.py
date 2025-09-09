from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.task import TaskStatus

from .attachment import AttachmentResponse


# Esquemas de entrada
class TaskBase(BaseModel):
    """Esquema base para tareas"""

    title: str = Field(
        ..., min_length=5, max_length=255, description="Título de la tarea"
    )
    description: Optional[str] = Field(None, description="Descripción de la tarea")
    position: int = Field(..., ge=0, description="Posición de la tarea en la fase")
    status: Optional[TaskStatus] = Field(
        TaskStatus.PENDING, description="Estado de la tarea"
    )
    start_date: Optional[datetime] = Field(
        None, description="Fecha de inicio de la tarea"
    )
    end_date: Optional[datetime] = Field(
        None, description="Fecha de finalización de la tarea"
    )
    completed: Optional[bool] = Field(
        False, description="Indica si la tarea está completada"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("El título de la tarea no puede estar vacío")
        if len(v.strip()) < 5:
            raise ValueError("El título de la tarea debe tener al menos 5 caracteres")
        return v.strip()

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v is not None and "start_date" in info.data:
            start_date = info.data["start_date"]
            if start_date is not None and v < start_date:
                raise ValueError(
                    "La fecha de finalización no puede ser anterior a la fecha de inicio"
                )
        return v


class TaskCreate(TaskBase):
    """Esquema para crear una tarea"""

    phase_id: int = Field(..., description="ID de la fase a la que pertenece la tarea")


class TaskUpdate(BaseModel):
    """Esquema para actualizar una tarea"""

    title: Optional[str] = Field(
        None, min_length=5, max_length=255, description="Título de la tarea"
    )
    description: Optional[str] = Field(None, description="Descripción de la tarea")
    position: Optional[int] = Field(
        None, ge=0, description="Posición de la tarea en la fase"
    )
    status: Optional[TaskStatus] = Field(None, description="Estado de la tarea")
    start_date: Optional[datetime] = Field(
        None, description="Fecha de inicio de la tarea"
    )
    end_date: Optional[datetime] = Field(
        None, description="Fecha de finalización de la tarea"
    )
    completed: Optional[bool] = Field(
        None, description="Indica si la tarea está completada"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or v.strip() == "":
                raise ValueError("El título de la tarea no puede estar vacío")
            if len(v.strip()) < 5:
                raise ValueError(
                    "El título de la tarea debe tener al menos 5 caracteres"
                )
            return v.strip()
        return v

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v is not None and "start_date" in info.data:
            start_date = info.data["start_date"]
            if start_date is not None and v < start_date:
                raise ValueError(
                    "La fecha de finalización no puede ser anterior a la fecha de inicio"
                )
        return v


# Esquemas de salida
class TaskResponse(TaskBase):
    """Esquema de respuesta para una tarea"""

    id: int
    phase_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """Esquema de respuesta para lista de tareas"""

    id: int
    title: str
    description: Optional[str]
    position: int
    status: TaskStatus
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    completed: bool
    phase_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# Esquema con relaciones anidadas
class TaskDetailResponse(TaskResponse):
    """Esquema de respuesta completo para tarea con todas sus relaciones"""

    attachment: Optional["AttachmentResponse"] = None

    model_config = {"from_attributes": True}
