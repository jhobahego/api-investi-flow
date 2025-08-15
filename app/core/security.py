from datetime import datetime, timedelta
from typing import Any, Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuración de seguridad para JWT
security = HTTPBearer()


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Crear un token de acceso JWT"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> str | None:
    """Verificar y decodificar un token JWT"""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
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


def get_current_user_email(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Obtener el email del usuario actual desde el token JWT"""
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    email = verify_token(token)
    if email is None:
        raise credential_exception
    return email


# Dependencia para obtener usuario actual
def get_current_user_dep(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session | None = None,
):
    """Dependencia para obtener el usuario actual desde la base de datos"""
    from app.database import get_db
    from app.services.user_service import user_service

    # Crear sesión de BD si no se proporciona
    if db is None:
        db = next(get_db())

    # Obtener email del token
    current_user_email = get_current_user_email(credentials)

    user = user_service.get_user_by_email(db, email=current_user_email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )

    if not bool(user.is_active):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario inactivo"
        )

    return user
