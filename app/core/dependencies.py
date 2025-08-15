"""Dependencias comunes de la aplicación"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import get_current_user_email
from app.database import get_db
from app.models.user import User
from app.services.user_service import user_service

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Dependencia para obtener el usuario actual"""
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
