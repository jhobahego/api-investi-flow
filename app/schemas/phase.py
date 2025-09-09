from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from .attachment import AttachmentResponse
from .task import TaskListResponse


# Esquemas de entrada
class PhaseBase(BaseModel):
    """Esquema base para fases"""

    name: str = Field(
        ..., min_length=5, max_length=255, description="Nombre de la fase"
    )
    position: int = Field(..., ge=0, description="Posición de la fase en el proyecto")
    color: Optional[str] = Field(
        None, max_length=7, description="Color de la fase en formato hexadecimal"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("El nombre de la fase no puede estar vacío")
        if len(v.strip()) < 5:
            raise ValueError("El nombre de la fase debe tener al menos 5 caracteres")
        return v.strip()

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Validar formato hexadecimal
            if not v.startswith("#") or len(v) != 7:
                raise ValueError("El color debe estar en formato hexadecimal (#RRGGBB)")
            try:
                int(v[1:], 16)
            except ValueError:
                raise ValueError("El color debe ser un valor hexadecimal válido")
        return v


class PhaseCreate(PhaseBase):
    """Esquema para crear una fase"""

    project_id: int = Field(..., description="ID del proyecto al que pertenece la fase")


class PhaseUpdate(BaseModel):
    """Esquema para actualizar una fase"""

    name: Optional[str] = Field(
        None, min_length=5, max_length=255, description="Nombre de la fase"
    )
    position: Optional[int] = Field(
        None, ge=0, description="Posición de la fase en el proyecto"
    )
    color: Optional[str] = Field(
        None, max_length=7, description="Color de la fase en formato hexadecimal"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or v.strip() == "":
                raise ValueError("El nombre de la fase no puede estar vacío")
            if len(v.strip()) < 5:
                raise ValueError(
                    "El nombre de la fase debe tener al menos 5 caracteres"
                )
            return v.strip()
        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.startswith("#") or len(v) != 7:
                raise ValueError("El color debe estar en formato hexadecimal (#RRGGBB)")
            try:
                int(v[1:], 16)
            except ValueError:
                raise ValueError("El color debe ser un valor hexadecimal válido")
        return v


class PhaseOrder(BaseModel):
    id: int
    position: int


class PhaseResponse(PhaseBase):
    """Esquema de respuesta para una fase"""

    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PhaseListResponse(BaseModel):
    """Esquema de respuesta para lista de fases"""

    id: int
    name: str
    position: int
    color: Optional[str]
    project_id: int

    model_config = {"from_attributes": True}


# Esquemas con relaciones anidadas
class PhaseWithTasksResponse(PhaseResponse):
    """Esquema de respuesta para fase con sus tareas"""

    tasks: List["TaskListResponse"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PhaseDetailResponse(PhaseResponse):
    """Esquema de respuesta completo para fase con todas sus relaciones"""

    tasks: List["TaskListResponse"] = Field(default_factory=list)
    attachment: Optional["AttachmentResponse"] = None

    model_config = {"from_attributes": True}
