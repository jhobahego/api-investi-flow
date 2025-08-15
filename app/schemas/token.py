from pydantic import BaseModel


class Token(BaseModel):
    """Esquema para la respuesta del token de acceso"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Esquema para los datos del token"""

    email: str | None = None


class LoginRequest(BaseModel):
    """Esquema para la solicitud de login"""

    email: str
    password: str
