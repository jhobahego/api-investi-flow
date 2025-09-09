from datetime import datetime, timedelta, timezone
from typing import Any, Union

from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuración de seguridad para JWT - OAuth2 para compatibilidad con Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Crear un token de acceso JWT"""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}

    secret_key = settings.SECRET_KEY
    if secret_key is None:
        raise ValueError("SECRET_KEY is not set in the configuration.")

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    """Crear un token de actualización JWT"""
    expire = datetime.now(timezone.utc) + timedelta(days=7)  # 7 días de expiración
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}

    secret_key = settings.SECRET_KEY
    if secret_key is None:
        raise ValueError("SECRET_KEY is not set in the configuration.")

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> str | None:
    """Verificar y decodificar un token JWT"""
    try:
        secret_key = settings.SECRET_KEY
        if secret_key is None:
            raise ValueError("SECRET_KEY is not set in the configuration.")

        payload = jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        if email is None:
            return None
        return str(email)
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar una contraseña plana contra su hash"""
    return pwd_context.verify(plain_password, hashed_password)  # type: ignore


def get_password_hash(password: str) -> str:
    """Generar el hash de una contraseña"""
    return pwd_context.hash(password)  # type: ignore
