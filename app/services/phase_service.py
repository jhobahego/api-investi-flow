from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.phase import Phase
from app.repositories.phase_repository import phase_repository
from app.repositories.project_repository import project_repository
from app.schemas.phase import PhaseCreate, PhaseUpdate
from app.services.base import BaseService


class PhaseService(BaseService[Phase, PhaseCreate, PhaseUpdate]):
    """Servicio para gestión de fases"""

    def __init__(self) -> None:
        super().__init__(phase_repository)

    def create_phase(self, db: Session, phase_in: PhaseCreate, owner_id: int) -> Phase:
        """
        Crear una nueva fase para un proyecto.

        Args:
            db: Sesión de base de datos
            phase_in: Datos de la fase a crear
            owner_id: ID del usuario propietario del proyecto

        Returns:
            Fase creada

        Raises:
            HTTPException: Si hay error en la validación o creación
        """
        try:
            # Verificar que el proyecto existe y pertenece al usuario
            project = project_repository.get_project_by_owner_and_id(
                db=db, project_id=phase_in.project_id, owner_id=owner_id
            )
            if not project:
                print(
                    f"Proyecto con ID {phase_in.project_id} no encontrado para el usuario {owner_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Proyecto no encontrado o no tienes permisos para acceder a él",
                )

            # Validar que el nombre no esté vacío
            if not phase_in.name or phase_in.name.strip() == "":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El nombre de la fase es requerido y no puede estar vacío",
                )

            # Si no se especifica posición, asignar la siguiente disponible
            if phase_in.position is None:
                max_position = phase_repository.get_max_position_by_project(
                    db=db, project_id=phase_in.project_id
                )
                phase_in.position = max_position + 1
            else:
                # Verificar si ya existe una fase en esa posición
                existing_phase = phase_repository.get_phase_by_project_and_position(
                    db=db, project_id=phase_in.project_id, position=phase_in.position
                )
                if existing_phase:
                    # Mover las fases posteriores una posición hacia adelante
                    phase_repository.update_phases_positions(
                        db=db,
                        project_id=phase_in.project_id,
                        from_position=phase_in.position,
                        increment=1,
                    )

            # Crear la fase
            phase = phase_repository.create_phase(db=db, phase_in=phase_in)
            return phase

        except HTTPException:
            raise
        except Exception as e:
            print(f"Error al crear la fase: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ha ocurrido un error al crear la fase",
            )

    def get_project_phases(
        self, db: Session, project_id: int, owner_id: int
    ) -> List[Phase]:
        """
        Obtener todas las fases de un proyecto.

        Args:
            db: Sesión de base de datos
            project_id: ID del proyecto
            owner_id: ID del usuario propietario

        Returns:
            Lista de fases del proyecto ordenadas por posición

        Raises:
            HTTPException: Si el proyecto no existe o no pertenece al usuario
        """
        try:
            # Verificar que el proyecto existe y pertenece al usuario
            project = project_repository.get_project_by_owner_and_id(
                db=db, project_id=project_id, owner_id=owner_id
            )
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Proyecto no encontrado o no tienes permisos para acceder a él",
                )

            phases = phase_repository.get_phases_by_project(
                db=db, project_id=project_id
            )
            return phases

        except HTTPException:
            raise
        except Exception as e:
            print(f"Error al obtener las fases: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ha ocurrido un error al obtener las fases del proyecto",
            )

    def get_phases_with_tasks(self, db: Session, phase_id: int) -> Optional[Phase]:
        """
        Obtener todas las fases de un proyecto con sus tareas asociadas.

        Args:
            db: Sesión de base de datos
            phase_id: ID de la fase

        Returns:
            Lista de fases con tareas asociadas

        Raises:
            HTTPException: Si la fase no existe
        """
        try:
            phase = phase_repository.get(db=db, id=phase_id)
            if not phase:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Fase no encontrada",
                )

            return phase_repository.get_phases_with_tasks(db=db, phase_id=phase_id)
        except HTTPException:
            raise

        except Exception as e:
            print(f"Error al obtener las fases con tareas: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ha ocurrido un error al intentar obtener las fases con tareas",
            )

    def get_phase_by_id(self, db: Session, phase_id: int, owner_id: int) -> Phase:
        """
        Obtener una fase específica por ID.

        Args:
            db: Sesión de base de datos
            phase_id: ID de la fase
            owner_id: ID del usuario propietario

        Returns:
            Fase encontrada

        Raises:
            HTTPException: Si la fase no existe o no pertenece al usuario
        """
        try:
            phase = phase_repository.get(db=db, id=phase_id)
            if not phase:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Fase no encontrada",
                )

            # Verificar que el proyecto de la fase pertenece al usuario
            project = project_repository.get_project_by_owner_and_id(
                db=db,
                project_id=phase.project_id,  # type: ignore
                owner_id=owner_id,
            )
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Fase no encontrada o no tienes permisos para acceder a ella",
                )

            return phase
        except HTTPException:
            raise

        except Exception as e:
            print(f"Error al obtener la fase: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ha ocurrido un error al obtener la fase",
            )

    def update_phase(
        self, db: Session, phase_id: int, phase_in: PhaseUpdate, owner_id: int
    ) -> Phase:
        """
        Actualizar una fase.

        Args:
            db: Sesión de base de datos
            phase_id: ID de la fase
            phase_in: Datos a actualizar
            owner_id: ID del usuario propietario

        Returns:
            Fase actualizada

        Raises:
            HTTPException: Si la fase no existe o no pertenece al usuario
        """
        # Verificar que la fase existe y pertenece al usuario
        phase = self.get_phase_by_id(db=db, phase_id=phase_id, owner_id=owner_id)

        try:
            # Si se está actualizando la posición
            if phase_in.position is not None and phase_in.position != phase.position:
                old_position = phase.position
                new_position = phase_in.position

                # Verificar si ya existe una fase en la nueva posición
                existing_phase = phase_repository.get_phase_by_project_and_position(
                    db=db,
                    project_id=phase.project_id,  # type: ignore
                    position=new_position,
                )

                if existing_phase and existing_phase.id != phase.id:  # type: ignore
                    if new_position < old_position:  # type: ignore
                        # Mover hacia arriba: incrementar posiciones entre new_position y old_position-1
                        phase_repository.update_phases_positions(
                            db=db,
                            project_id=phase.project_id,  # type: ignore
                            from_position=new_position,
                            increment=1,
                        )
                        # Actualizar posiciones hasta la anterior posición de la fase actual
                        phases_to_update = (
                            db.query(Phase)
                            .filter(
                                Phase.project_id == phase.project_id,
                                Phase.position >= new_position,
                                Phase.position < old_position,
                                Phase.id != phase.id,
                            )
                            .all()
                        )
                        for p in phases_to_update:
                            p.position += 1  # type: ignore
                    else:
                        # Mover hacia abajo: decrementar posiciones entre old_position+1 y new_position
                        phases_to_update = (
                            db.query(Phase)
                            .filter(
                                Phase.project_id == phase.project_id,
                                Phase.position > old_position,
                                Phase.position <= new_position,
                                Phase.id != phase.id,
                            )
                            .all()
                        )
                        for p in phases_to_update:
                            p.position -= 1  # type: ignore

                    db.flush()  # Aplicar cambios antes de actualizar la fase actual

            # Actualizar la fase
            updated_phase = phase_repository.update_phase(
                db=db, phase=phase, phase_in=phase_in
            )
            return updated_phase

        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            print(f"Error al actualizar la fase: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ha ocurrido un error al actualizar la fase",
            )

    def delete_phase(self, db: Session, phase_id: int, owner_id: int) -> bool:
        """
        Eliminar una fase.

        Args:
            db: Sesión de base de datos
            phase_id: ID de la fase
            owner_id: ID del usuario propietario

        Returns:
            True si se eliminó correctamente

        Raises:
            HTTPException: Si la fase no existe o no pertenece al usuario
        """
        # Verificar que la fase existe y pertenece al usuario
        phase = self.get_phase_by_id(db=db, phase_id=phase_id, owner_id=owner_id)

        try:
            # Eliminar la fase y actualizar posiciones
            phase_repository.delete_phase_and_update_positions(db=db, phase=phase)
            return True

        except Exception as e:
            db.rollback()
            print(f"Error al eliminar la fase: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ha ocurrido un error al eliminar la fase",
            )

    def reorder_phases(
        self, db: Session, project_id: int, phase_orders: List[dict], owner_id: int
    ) -> List[Phase]:
        """
        Reordenar las fases de un proyecto.

        Args:
            db: Sesión de base de datos
            project_id: ID del proyecto
            phase_orders: Lista de diccionarios con id y position de cada fase
            owner_id: ID del usuario propietario

        Returns:
            Lista de fases reordenadas

        Raises:
            HTTPException: Si hay error en la validación o reordenamiento
        """
        try:
            # Verificar que el proyecto existe y pertenece al usuario
            project = project_repository.get_project_by_owner_and_id(
                db=db, project_id=project_id, owner_id=owner_id
            )
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Proyecto no encontrado o no tienes permisos para acceder a él",
                )

            # Obtener todas las fases del proyecto
            phases = phase_repository.get_phases_by_project(
                db=db, project_id=project_id
            )
            phase_dict = {phase.id: phase for phase in phases}

            # Validar que todas las fases en phase_orders existen
            for order in phase_orders:
                phase_id = order.get("id")
                if phase_id not in phase_dict:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Fase con ID {phase_id} no encontrada en el proyecto",
                    )

            # Actualizar las posiciones
            for order in phase_orders:
                phase_id = order.get("id")
                new_position = order.get("position")
                phase = phase_dict[phase_id]  # type: ignore
                phase.position = new_position  # type: ignore

            db.commit()

            # Retornar las fases ordenadas
            return phase_repository.get_phases_by_project(db=db, project_id=project_id)

        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            print(f"Error al reordenar las fases: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ha ocurrido un error al reordenar las fases",
            )


# Instancia global del servicio
phase_service = PhaseService()
