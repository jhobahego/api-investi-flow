from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UserBase(BaseModel):
    """Esquema base para User"""

    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    """Esquema para crear un usuario"""

    password: str

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
