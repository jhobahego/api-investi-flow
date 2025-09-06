from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.project import Project
from app.repositories.project_repository import project_repository
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.base import BaseService


class ProjectService(BaseService[Project, ProjectCreate, ProjectUpdate]):
    """Servicio para gestión de proyectos"""

    def __init__(self) -> None:
        super().__init__(project_repository)

    def create_project(
        self, db: Session, project_in: ProjectCreate, owner_id: int
    ) -> Project:
        """
        Crear un nuevo proyecto para un usuario.

        Args:
            db: Sesión de base de datos
            project_in: Datos del proyecto a crear
            owner_id: ID del usuario propietario

        Returns:
            Proyecto creado

        Raises:
            HTTPException: Si hay error en la validación o creación
        """
        try:
            # Validar que el nombre no esté vacío
            if not project_in.name or project_in.name.strip() == "":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El nombre del proyecto es requerido y no puede estar vacío",
                )

            # Crear el proyecto
            project = project_repository.create_project(
                db=db, project_in=project_in, owner_id=owner_id
            )
            return project

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al crear el proyecto: {str(e)}",
            )

    def get_user_projects(self, db: Session, owner_id: int) -> List[Project]:
        """
        Obtener todos los proyectos de un usuario.

        Args:
            db: Sesión de base de datos
            owner_id: ID del usuario propietario

        Returns:
            Lista de proyectos del usuario
        """
        try:
            projects = project_repository.get_projects_by_owner(
                db=db, owner_id=owner_id
            )
            return projects

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener los proyectos: {str(e)}",
            )

    def get_user_project_by_id(
        self, db: Session, project_id: int, owner_id: int
    ) -> Project:
        """
        Obtener un proyecto específico de un usuario.

        Args:
            db: Sesión de base de datos
            project_id: ID del proyecto
            owner_id: ID del usuario propietario

        Returns:
            Proyecto encontrado

        Raises:
            HTTPException: Si el proyecto no existe o no pertenece al usuario
        """
        project = project_repository.get_project_by_owner_and_id(
            db=db, project_id=project_id, owner_id=owner_id
        )

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto no encontrado o no tienes permisos para acceder a él",
            )

        return project

    def update_user_project(
        self, db: Session, project_id: int, project_in: ProjectUpdate, owner_id: int
    ) -> Project:
        """
        Actualizar un proyecto de un usuario.

        Args:
            db: Sesión de base de datos
            project_id: ID del proyecto
            project_in: Datos a actualizar
            owner_id: ID del usuario propietario

        Returns:
            Proyecto actualizado

        Raises:
            HTTPException: Si el proyecto no existe o no pertenece al usuario
        """
        # Verificar que el proyecto existe y pertenece al usuario
        project = self.get_user_project_by_id(
            db=db, project_id=project_id, owner_id=owner_id
        )

        try:
            # Actualizar el proyecto
            updated_project = project_repository.update_project(
                db=db, project=project, project_in=project_in
            )
            return updated_project

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al actualizar el proyecto: {str(e)}",
            )

    def delete_user_project(self, db: Session, project_id: int, owner_id: int) -> bool:
        """
        Eliminar un proyecto de un usuario.

        Args:
            db: Sesión de base de datos
            project_id: ID del proyecto
            owner_id: ID del usuario propietario

        Returns:
            True si se eliminó correctamente

        Raises:
            HTTPException: Si el proyecto no existe o no pertenece al usuario
        """
        # Verificar que el proyecto existe y pertenece al usuario
        project = self.get_user_project_by_id(
            db=db, project_id=project_id, owner_id=owner_id
        )

        try:
            # Eliminar el proyecto
            db.delete(project)
            db.commit()
            return True

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al eliminar el proyecto: {str(e)}",
            )

    def get_project_with_phases(
        self, db: Session, project_id: int, owner_id: int
    ) -> Optional[Project]:
        """
        Obtener todas las fases de un proyecto de un usuario.

        Args:
            db: Sesión de base de datos
            project_id: ID del proyecto
            owner_id: ID del usuario propietario

        Returns:
            Lista de fases del proyecto

        Raises:
            HTTPException: Si el proyecto no existe o no pertenece al usuario
        """

        try:
            project = project_repository.get(db=db, id=project_id)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Proyecto no encontrado",
                )

            # Verificar que el proyecto pertenece al usuario
            project = project_repository.get_project_by_owner_and_id(
                db=db, project_id=project_id, owner_id=owner_id
            )
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Proyecto no encontrado o no tienes permisos para acceder a él",
                )

            phases = project_repository.get_project_with_phases(
                db=db, project_id=project_id
            )
            return phases
        except HTTPException:
            raise

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener las fases del proyecto: {str(e)}",
            )


# Instancia global del servicio
project_service = ProjectService()
