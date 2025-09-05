from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.attachment import FileType


# Esquemas de entrada
class AttachmentBase(BaseModel):
    """Esquema base para adjuntos"""

    file_name: str = Field(
        ..., min_length=1, max_length=255, description="Nombre del archivo"
    )
    file_type: FileType = Field(..., description="Tipo de archivo")
    file_size: int = Field(..., gt=0, description="Tamaño del archivo en bytes")

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("El nombre del archivo no puede estar vacío")
        return v.strip()

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        # Límite de 50MB (50 * 1024 * 1024 bytes)
        max_size = 50 * 1024 * 1024
        if v > max_size:
            raise ValueError("El archivo no puede ser mayor a 50MB")
        return v


class AttachmentCreate(AttachmentBase):
    """Esquema para crear un adjunto"""

    file_path: str = Field(..., description="Ruta del archivo en el sistema")
    # Solo uno de estos debe estar presente
    project_id: Optional[int] = Field(None, description="ID del proyecto")
    phase_id: Optional[int] = Field(None, description="ID de la fase")
    task_id: Optional[int] = Field(None, description="ID de la tarea")

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("La ruta del archivo no puede estar vacía")
        return v.strip()

    def __init__(self, **data):
        super().__init__(**data)
        # Validar que solo uno de los IDs padre esté presente
        parent_ids = [self.project_id, self.phase_id, self.task_id]
        non_null_count = sum(1 for pid in parent_ids if pid is not None)

        if non_null_count != 1:
            raise ValueError(
                "Debe especificar exactamente uno de: project_id, phase_id o task_id"
            )


class AttachmentUpdate(BaseModel):
    """Esquema para actualizar un adjunto"""

    file_name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Nombre del archivo"
    )

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or v.strip() == "":
                raise ValueError("El nombre del archivo no puede estar vacío")
            return v.strip()
        return v


# Esquemas de salida
class AttachmentResponse(AttachmentBase):
    """Esquema de respuesta para un adjunto"""

    id: int
    file_path: str
    project_id: Optional[int]
    phase_id: Optional[int]
    task_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AttachmentListResponse(BaseModel):
    """Esquema de respuesta para lista de adjuntos"""

    id: int
    file_name: str
    file_type: FileType
    file_size: int
    project_id: Optional[int]
    phase_id: Optional[int]
    task_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}
