from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import Base
from app.repositories.base import BaseRepository

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Servicio base con operaciones comunes"""

    def __init__(
        self, repository: BaseRepository[ModelType, CreateSchemaType, UpdateSchemaType]
    ):
        self.repository = repository

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """Obtener un registro por ID"""
        return self.repository.get(db, id)

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """Obtener múltiples registros con paginación"""
        return self.repository.get_multi(db, skip=skip, limit=limit)

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """Crear un nuevo registro"""
        return self.repository.create(db, obj_in=obj_in)

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        """Actualizar un registro"""
        return self.repository.update(db, db_obj=db_obj, obj_in=obj_in)

    def remove(self, db: Session, *, id: int) -> Optional[ModelType]:
        """Eliminar un registro por ID"""
        return self.repository.remove(db, id=id)
