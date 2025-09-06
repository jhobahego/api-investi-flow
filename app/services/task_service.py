from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.task import Task
from app.repositories.phase_repository import phase_repository
from app.repositories.project_repository import project_repository
from app.repositories.task_repository import task_repository
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.base import BaseService


class TaskService(BaseService[Task, TaskCreate, TaskUpdate]):
    """Servicio para gestión de tareas"""

    def __init__(self) -> None:
        super().__init__(task_repository)

    def create_task(self, db: Session, task_in: TaskCreate, owner_id: int) -> Task:
        """
        Crear una nueva tarea para una fase.

        Args:
            db: Sesión de base de datos
            task_in: Datos de la tarea a crear
            owner_id: ID del usuario propietario del proyecto

        Returns:
            Tarea creada

        Raises:
            HTTPException: Si hay error en la validación o creación
        """
        try:
            # Verificar que la fase existe y pertenece a un proyecto del usuario
            phase = phase_repository.get(db=db, id=task_in.phase_id)
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
                    detail="No tienes permisos para crear tareas en esta fase",
                )

            # Validar que el título no esté vacío
            if not task_in.title or task_in.title.strip() == "":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El título de la tarea es requerido y no puede estar vacío",
                )

            # Si no se especifica posición, asignar la siguiente disponible (auto-incremental)
            if task_in.position is None:
                max_position = task_repository.get_max_position_by_phase(
                    db=db, phase_id=task_in.phase_id
                )
                task_in.position = max_position + 1
            else:
                # Verificar si ya existe una tarea en esa posición
                existing_task = task_repository.get_task_by_phase_and_position(
                    db=db, phase_id=task_in.phase_id, position=task_in.position
                )
                if existing_task:
                    # Mover las tareas posteriores una posición hacia adelante
                    task_repository.update_tasks_positions(
                        db=db,
                        phase_id=task_in.phase_id,
                        from_position=task_in.position,
                        increment=1,
                    )

            # Crear la tarea
            task = task_repository.create_task(db=db, task_in=task_in)
            return task

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al crear la tarea: {str(e)}",
            )

    def get_phase_tasks(self, db: Session, phase_id: int, owner_id: int) -> List[Task]:
        """
        Obtener todas las tareas de una fase.

        Args:
            db: Sesión de base de datos
            phase_id: ID de la fase
            owner_id: ID del usuario propietario

        Returns:
            Lista de tareas de la fase ordenadas por posición

        Raises:
            HTTPException: Si la fase no existe o no pertenece al usuario
        """
        try:
            # Verificar que la fase existe y pertenece a un proyecto del usuario
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
                    detail="No tienes permisos para acceder a las tareas de esta fase",
                )

            tasks = task_repository.get_tasks_by_phase(db=db, phase_id=phase_id)
            return tasks

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener las tareas: {str(e)}",
            )

    def get_project_tasks(
        self, db: Session, project_id: int, owner_id: int
    ) -> List[Task]:
        """
        Obtener todas las tareas de un proyecto.

        Args:
            db: Sesión de base de datos
            project_id: ID del proyecto
            owner_id: ID del usuario propietario

        Returns:
            Lista de tareas del proyecto ordenadas por fase y posición

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

            tasks = task_repository.get_tasks_by_project(db=db, project_id=project_id)
            return tasks

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener las tareas del proyecto: {str(e)}",
            )

    def get_task_by_id(self, db: Session, task_id: int, owner_id: int) -> Task:
        """
        Obtener una tarea específica por ID.

        Args:
            db: Sesión de base de datos
            task_id: ID de la tarea
            owner_id: ID del usuario propietario

        Returns:
            Tarea encontrada

        Raises:
            HTTPException: Si la tarea no existe o no pertenece al usuario
        """
        task = task_repository.get(db=db, id=task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarea no encontrada",
            )

        # Verificar que la fase de la tarea pertenece a un proyecto del usuario
        phase = phase_repository.get(db=db, id=task.phase_id)
        if not phase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarea no encontrada",
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
                detail="Tarea no encontrada o no tienes permisos para acceder a ella",
            )

        return task

    def update_task(
        self, db: Session, task_id: int, task_in: TaskUpdate, owner_id: int
    ) -> Task:
        """
        Actualizar una tarea.

        Args:
            db: Sesión de base de datos
            task_id: ID de la tarea
            task_in: Datos a actualizar
            owner_id: ID del usuario propietario

        Returns:
            Tarea actualizada

        Raises:
            HTTPException: Si la tarea no existe o no pertenece al usuario
        """
        # Verificar que la tarea existe y pertenece al usuario
        task = self.get_task_by_id(db=db, task_id=task_id, owner_id=owner_id)

        try:
            # Si se está actualizando la posición dentro de la misma fase
            if task_in.position is not None and task_in.position != task.position:
                old_position = task.position
                new_position = task_in.position

                # Verificar si ya existe una tarea en la nueva posición
                existing_task = task_repository.get_task_by_phase_and_position(
                    db=db,
                    phase_id=task.phase_id,  # type: ignore
                    position=new_position,
                )

                if existing_task and existing_task.id != task.id:  # type: ignore
                    if new_position < old_position:  # type: ignore
                        # Mover hacia arriba: incrementar posiciones entre new_position y old_position-1
                        tasks_to_update = (
                            db.query(Task)
                            .filter(
                                Task.phase_id == task.phase_id,
                                Task.position >= new_position,
                                Task.position < old_position,
                                Task.id != task.id,
                            )
                            .all()
                        )
                        for t in tasks_to_update:
                            setattr(t, "position", t.position + 1)
                    else:
                        # Mover hacia abajo: decrementar posiciones entre old_position+1 y new_position
                        tasks_to_update = (
                            db.query(Task)
                            .filter(
                                Task.phase_id == task.phase_id,
                                Task.position > old_position,
                                Task.position <= new_position,
                                Task.id != task.id,
                            )
                            .all()
                        )
                        for t in tasks_to_update:
                            setattr(t, "position", t.position - 1)

                    db.flush()  # Aplicar cambios antes de actualizar la tarea actual

            # Actualizar la tarea
            updated_task = task_repository.update_task(
                db=db, task=task, task_in=task_in
            )
            return updated_task

        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al actualizar la tarea: {str(e)}",
            )

    def delete_task(self, db: Session, task_id: int, owner_id: int) -> bool:
        """
        Eliminar una tarea.

        Args:
            db: Sesión de base de datos
            task_id: ID de la tarea
            owner_id: ID del usuario propietario

        Returns:
            True si se eliminó correctamente

        Raises:
            HTTPException: Si la tarea no existe o no pertenece al usuario
        """
        # Verificar que la tarea existe y pertenece al usuario
        task = self.get_task_by_id(db=db, task_id=task_id, owner_id=owner_id)

        try:
            # Eliminar la tarea y actualizar posiciones
            task_repository.delete_task_and_update_positions(db=db, task=task)
            return True

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al eliminar la tarea: {str(e)}",
            )

    def move_task_to_phase(
        self,
        db: Session,
        task_id: int,
        new_phase_id: int,
        new_position: Optional[int],
        owner_id: int,
    ) -> Task:
        """
        Mover una tarea a otra fase.

        Args:
            db: Sesión de base de datos
            task_id: ID de la tarea
            new_phase_id: ID de la nueva fase
            new_position: Nueva posición (opcional)
            owner_id: ID del usuario propietario

        Returns:
            Tarea actualizada

        Raises:
            HTTPException: Si la tarea o fase no existen o no pertenecen al usuario
        """
        # Verificar que la tarea existe y pertenece al usuario
        task = self.get_task_by_id(db=db, task_id=task_id, owner_id=owner_id)

        # Verificar que la nueva fase existe y pertenece a un proyecto del usuario
        new_phase = phase_repository.get(db=db, id=new_phase_id)
        if not new_phase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fase destino no encontrada",
            )

        # Verificar que el proyecto de la nueva fase pertenece al usuario
        project = project_repository.get_project_by_owner_and_id(
            db=db,
            project_id=new_phase.project_id,  # type: ignore
            owner_id=owner_id,
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No tienes permisos para mover la tarea a esta fase",
            )

        try:
            # Mover la tarea a la nueva fase
            updated_task = task_repository.move_task_to_phase(
                db=db, task=task, new_phase_id=new_phase_id, new_position=new_position
            )
            return updated_task

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al mover la tarea: {str(e)}",
            )

    def reorder_tasks_in_phase(
        self, db: Session, phase_id: int, task_orders: List[dict], owner_id: int
    ) -> List[Task]:
        """
        Reordenar las tareas de una fase.

        Args:
            db: Sesión de base de datos
            phase_id: ID de la fase
            task_orders: Lista de diccionarios con id y position de cada tarea
            owner_id: ID del usuario propietario

        Returns:
            Lista de tareas reordenadas

        Raises:
            HTTPException: Si hay error en la validación o reordenamiento
        """
        try:
            # Verificar que la fase existe y pertenece a un proyecto del usuario
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
                    detail="No tienes permisos para reordenar las tareas de esta fase",
                )

            # Obtener todas las tareas de la fase
            tasks = task_repository.get_tasks_by_phase(db=db, phase_id=phase_id)
            task_dict = {task.id: task for task in tasks}

            # Validar que todas las tareas en task_orders existen
            for order in task_orders:
                task_id = order.get("id")
                if task_id not in task_dict:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Tarea con ID {task_id} no encontrada en la fase",
                    )

            # Actualizar las posiciones
            for order in task_orders:
                task_id = order.get("id")
                new_position = order.get("position")
                task = task_dict[task_id]  # type: ignore
                setattr(task, "position", new_position)

            db.commit()

            # Retornar las tareas ordenadas
            return task_repository.get_tasks_by_phase(db=db, phase_id=phase_id)

        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al reordenar las tareas: {str(e)}",
            )


# Instancia global del servicio
task_service = TaskService()
