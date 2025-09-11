from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.phase import Phase
from app.models.task import Task
from app.repositories.base import BaseRepository
from app.schemas.phase import PhaseCreate, PhaseUpdate


class PhaseRepository(BaseRepository[Phase, PhaseCreate, PhaseUpdate]):
    """Repositorio para gestión de fases"""

    def __init__(self) -> None:
        super().__init__(Phase)

    def get_phases_by_project(self, db: Session, project_id: int) -> List[Phase]:
        """Obtener todas las fases de un proyecto específico ordenadas por posición"""
        return (
            db.query(self.model)
            .filter(Phase.project_id == project_id)
            .order_by(Phase.position)
            .all()
        )

    def get_phase_by_project_and_id(
        self, db: Session, phase_id: int, project_id: int
    ) -> Optional[Phase]:
        """Obtener una fase específica de un proyecto"""
        return (
            db.query(self.model)
            .filter(Phase.id == phase_id, Phase.project_id == project_id)
            .first()
        )

    def get_phase_by_project_and_position(
        self, db: Session, project_id: int, position: int
    ) -> Optional[Phase]:
        """Obtener una fase por su posición en un proyecto"""
        return (
            db.query(self.model)
            .filter(Phase.project_id == project_id, Phase.position == position)
            .first()
        )

    def get_max_position_by_project(self, db: Session, project_id: int) -> int:
        """Obtener la posición máxima de las fases en un proyecto"""
        max_position = (
            db.query(self.model.position)
            .filter(Phase.project_id == project_id)
            .order_by(Phase.position.desc())
            .first()
        )
        return max_position[0] if max_position else -1

    def create_phase(self, db: Session, phase_in: PhaseCreate) -> Phase:
        """Crear una nueva fase"""
        phase_data = phase_in.model_dump()
        phase = Phase(**phase_data)

        db.add(phase)
        db.commit()
        db.refresh(phase)
        return phase

    def update_phase(self, db: Session, phase: Phase, phase_in: PhaseUpdate) -> Phase:
        """Actualizar una fase existente"""
        update_data = phase_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(phase, field, value)

        db.commit()
        db.refresh(phase)
        return phase

    def update_phases_positions(
        self, db: Session, project_id: int, from_position: int, increment: int = 1
    ) -> None:
        """
        Actualizar las posiciones de las fases cuando se inserta o elimina una fase.

        Args:
            db: Sesión de base de datos
            project_id: ID del proyecto
            from_position: Posición desde la cual actualizar
            increment: Incremento a aplicar (1 para insertar, -1 para eliminar)
        """
        phases_to_update = (
            db.query(self.model)
            .filter(Phase.project_id == project_id, Phase.position >= from_position)
            .all()
        )

        for phase in phases_to_update:
            setattr(phase, "position", phase.position + increment)

        db.commit()

    def delete_phase_and_update_positions(self, db: Session, phase: Phase) -> None:
        """
        Eliminar una fase y actualizar las posiciones de las fases posteriores
        """
        project_id = phase.project_id
        deleted_position = phase.position

        # Eliminar la fase
        db.delete(phase)
        db.flush()  # Asegurar que el delete se ejecute antes de las actualizaciones

        # Actualizar posiciones de las fases posteriores
        self.update_phases_positions(
            db=db,
            project_id=project_id,  # type: ignore
            from_position=deleted_position + 1,  # type: ignore
            increment=-1,
        )

        db.commit()

    def get_phase_tasks(self, db: Session, phase_id: int) -> List[Task]:
        """Obtener todas las tareas de una fase específica"""
        return db.query(Task).filter(Task.phase_id == phase_id).all()


# Instancia global del repositorio
phase_repository = PhaseRepository()
