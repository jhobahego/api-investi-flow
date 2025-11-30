from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.project import ProjectStatus, ResearchType

from .attachment import AttachmentResponse
from .phase import PhaseListResponse, PhaseResponse


# Esquemas de entrada
class ProjectBase(BaseModel):
    """Esquema base para proyectos"""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Nombre del proyecto"
    )
    description: Optional[str] = Field(None, description="Descripción del proyecto")
    research_type: Optional[ResearchType] = Field(
        None, description="Tipo de investigación"
    )
    institution: Optional[str] = Field(None, max_length=255, description="Institución")
    research_group: Optional[str] = Field(
        None, max_length=255, description="Grupo de investigación"
    )
    category: Optional[str] = Field(
        None, max_length=100, description="Categoría del proyecto"
    )
    status: Optional[ProjectStatus] = Field(
        ProjectStatus.PLANNING, description="Estado del proyecto"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("El nombre del proyecto no puede estar vacío")
        return v.strip()


class ProjectCreate(ProjectBase):
    """Esquema para crear un proyecto"""

    pass


class ProjectUpdate(BaseModel):
    """Esquema para actualizar un proyecto"""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Nombre del proyecto"
    )
    description: Optional[str] = Field(None, description="Descripción del proyecto")
    research_type: Optional[ResearchType] = Field(
        None, description="Tipo de investigación"
    )
    institution: Optional[str] = Field(None, max_length=255, description="Institución")
    research_group: Optional[str] = Field(
        None, max_length=255, description="Grupo de investigación"
    )
    category: Optional[str] = Field(
        None, max_length=100, description="Categoría del proyecto"
    )
    status: Optional[ProjectStatus] = Field(None, description="Estado del proyecto")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or v.strip() == "":
                raise ValueError("El nombre del proyecto no puede estar vacío")
            return v.strip()
        return v


# Esquemas de salida
class ProjectResponse(ProjectBase):
    """Esquema de respuesta para un proyecto"""

    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """Esquema de respuesta para lista de proyectos"""

    id: int
    name: str
    description: Optional[str]
    status: ProjectStatus
    research_type: Optional[ResearchType]
    category: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Esquemas con relaciones anidadas (para respuestas detalladas)
class ProjectWithPhasesResponse(ProjectResponse):
    """Esquema de respuesta para proyecto con sus fases"""

    # Se importarán dinámicamente para evitar imports circulares
    phases: List["PhaseListResponse"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ProjectDetailResponse(ProjectResponse):
    """Esquema de respuesta completo para proyecto con todas sus relaciones"""

    # Se importarán dinámicamente para evitar imports circulares
    phases: List["PhaseListResponse"] = Field(default_factory=list)
    attachment: Optional["AttachmentResponse"] = None

    model_config = {"from_attributes": True}
