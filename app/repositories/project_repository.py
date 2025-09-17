from typing import Any, List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.project import Project
from app.repositories.base import BaseRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectRepository(BaseRepository[Project, ProjectCreate, ProjectUpdate]):
    """Repositorio para gestión de proyectos"""

    def __init__(self) -> None:
        super().__init__(Project)

    def get_projects_by_owner(self, db: Session, owner_id: int) -> List[Project]:
        """Obtener todos los proyectos de un usuario específico"""
        return db.query(self.model).filter(Project.owner_id == owner_id).all()

    def get_project_by_owner_and_id(
        self, db: Session, project_id: int, owner_id: int
    ) -> Optional[Project]:
        """Obtener un proyecto específico de un usuario"""
        return (
            db.query(self.model)
            .filter(Project.id == project_id, Project.owner_id == owner_id)
            .first()
        )

    def create_project(
        self, db: Session, project_in: ProjectCreate, owner_id: int
    ) -> Project:
        """Crear un nuevo proyecto"""
        project_data = project_in.model_dump()
        project_data["owner_id"] = owner_id
        project = Project(**project_data)

        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    def update_project(
        self, db: Session, project: Project, project_in: ProjectUpdate
    ) -> Project:
        """Actualizar un proyecto existente"""
        update_data = project_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(project, field, value)

        db.commit()
        db.refresh(project)
        return project

    def get_project_with_phases(
        self, db: Session, project_id: int
    ) -> Optional[Project]:
        """Obtener todas las fases asociadas a un proyecto"""
        return (
            db.query(Project)
            .filter(Project.id == project_id)
            .options(joinedload(Project.phases))
            .first()
        )

    def search_projects_by_name(
        self, db: Session, query: str, owner_id: int
    ) -> list[type[Project]]:
        """Buscar proyectos por nombre que contengan una subcadena específica"""
        return (
            db.query(self.model)
            .filter(
                Project.name.ilike(f"%{query}%"),
                Project.owner_id == owner_id,
            )
            .all()
        )


# Instancia global del repositorio
project_repository = ProjectRepository()
