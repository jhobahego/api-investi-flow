import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UserBase(BaseModel):
    """Esquema base para User"""

    email: EmailStr
    full_name: str
    phone_number: Optional[
        str
    ] = None  # Opcional para compatibilidad con usuarios existentes
    university: Optional[str] = None
    research_group: Optional[str] = None
    career: Optional[str] = None


class UserCreate(BaseModel):
    """Esquema para crear un usuario"""

    email: EmailStr
    full_name: str
    password: str
    phone_number: str  # Requerido para nuevos usuarios
    university: Optional[str] = None
    research_group: Optional[str] = None
    career: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validar que la contraseña cumple con los requisitos de seguridad"""
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")

        if not any(char.isupper() for char in v):
            raise ValueError("La contraseña debe tener al menos una letra mayúscula")

        if not any(char.islower() for char in v):
            raise ValueError("La contraseña debe tener al menos una letra minúscula")

        if not any(char.isdigit() for char in v):
            raise ValueError("La contraseña debe tener al menos un número")

        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """Validar el nombre completo"""
        if len(v.strip()) < 2:
            raise ValueError("El nombre completo debe tener al menos 2 caracteres")
        return v.strip()

    @field_validator("phone_number")
    @classmethod
    def validate_colombian_phone(cls, v: str) -> str:
        """Validar formato de teléfono colombiano"""
        pattern = r"^\+57[13-8]\d{7,9}$|^\+573\d{9}$"
        if not re.match(pattern, v):
            raise ValueError(
                "El número debe tener formato colombiano válido: "
                "+57 seguido del número (ej: +573001234567 para móvil, +5714567890 para fijo)"
            )
        return v

    @field_validator("university")
    @classmethod
    def validate_university(cls, v: Optional[str]) -> Optional[str]:
        """Validar universidad (opcional)"""
        if v is not None and len(v.strip()) < 2:
            raise ValueError(
                "El nombre de la universidad debe tener al menos 2 caracteres"
            )
        return v.strip() if v else None

    @field_validator("research_group")
    @classmethod
    def validate_research_group(cls, v: Optional[str]) -> Optional[str]:
        """Validar semillero de investigación (opcional)"""
        if v is not None and len(v.strip()) < 2:
            raise ValueError("El nombre del semillero debe tener al menos 2 caracteres")
        return v.strip() if v else None

    @field_validator("career")
    @classmethod
    def validate_career(cls, v: Optional[str]) -> Optional[str]:
        """Validar carrera (opcional)"""
        if v is not None and len(v.strip()) < 2:
            raise ValueError("El nombre de la carrera debe tener al menos 2 caracteres")
        return v.strip() if v else None


class UserResponse(UserBase):
    """Esquema para respuesta de usuario (sin contraseña)"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class UserInDB(UserBase):
    """Esquema para usuario en base de datos"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    hashed_password: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    """Esquema para actualizar un usuario (todos los campos opcionales)"""

    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    university: Optional[str] = None
    research_group: Optional[str] = None
    career: Optional[str] = None

    @field_validator("phone_number")
    @classmethod
    def validate_colombian_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validar formato de teléfono colombiano"""
        if v is not None:
            pattern = r"^\+57[13-8]\d{7,9}$|^\+573\d{9}$"
            if not re.match(pattern, v):
                raise ValueError(
                    "El número debe tener formato colombiano válido: "
                    "+57 seguido del número (ej: +573001234567 para móvil, +5714567890 para fijo)"
                )
        return v

    @field_validator("full_name", "university", "research_group", "career")
    @classmethod
    def validate_non_empty_strings(cls, v: Optional[str]) -> Optional[str]:
        """Validar que los strings no estén vacíos"""
        if v is not None and len(v.strip()) < 2:
            raise ValueError("El campo debe tener al menos 2 caracteres")
        return v.strip() if v else None
