from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.task import Task
from app.repositories.base import BaseRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskRepository(BaseRepository[Task, TaskCreate, TaskUpdate]):
    """Repositorio para gestión de tareas"""

    def __init__(self) -> None:
        super().__init__(Task)

    def get_tasks_by_phase(self, db: Session, phase_id: int) -> List[Task]:
        """Obtener todas las tareas de una fase específica ordenadas por posición"""
        return (
            db.query(self.model)
            .filter(Task.phase_id == phase_id)
            .order_by(Task.position)
            .all()
        )

    def get_task_by_phase_and_id(
        self, db: Session, task_id: int, phase_id: int
    ) -> Optional[Task]:
        """Obtener una tarea específica de una fase"""
        return (
            db.query(self.model)
            .filter(Task.id == task_id, Task.phase_id == phase_id)
            .first()
        )

    def get_task_by_phase_and_position(
        self, db: Session, phase_id: int, position: int
    ) -> Optional[Task]:
        """Obtener una tarea por su posición en una fase"""
        return (
            db.query(self.model)
            .filter(Task.phase_id == phase_id, Task.position == position)
            .first()
        )

    def get_max_position_by_phase(self, db: Session, phase_id: int) -> int:
        """Obtener la posición máxima de las tareas en una fase"""
        max_position = (
            db.query(self.model.position)
            .filter(Task.phase_id == phase_id)
            .order_by(Task.position.desc())
            .first()
        )
        return max_position[0] if max_position else -1

    def get_tasks_by_project(self, db: Session, project_id: int) -> List[Task]:
        """Obtener todas las tareas de un proyecto a través de sus fases"""
        from app.models.phase import Phase

        return (
            db.query(self.model)
            .join(Phase, Task.phase_id == Phase.id)
            .filter(Phase.project_id == project_id)
            .order_by(Phase.position, Task.position)
            .all()
        )

    def create_task(self, db: Session, task_in: TaskCreate) -> Task:
        """Crear una nueva tarea"""
        task_data = task_in.model_dump()
        task = Task(**task_data)

        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def update_task(self, db: Session, task: Task, task_in: TaskUpdate) -> Task:
        """Actualizar una tarea existente"""
        update_data = task_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(task, field, value)

        db.commit()
        db.refresh(task)
        return task

    def update_tasks_positions(
        self, db: Session, phase_id: int, from_position: int, increment: int = 1
    ) -> None:
        """
        Actualizar las posiciones de las tareas cuando se inserta o elimina una tarea.

        Args:
            db: Sesión de base de datos
            phase_id: ID de la fase
            from_position: Posición desde la cual actualizar
            increment: Incremento a aplicar (1 para insertar, -1 para eliminar)
        """
        tasks_to_update = (
            db.query(self.model)
            .filter(Task.phase_id == phase_id, Task.position >= from_position)
            .all()
        )

        for task in tasks_to_update:
            setattr(task, "position", task.position + increment)

        db.commit()

    def delete_task_and_update_positions(self, db: Session, task: Task) -> None:
        """
        Eliminar una tarea y actualizar las posiciones de las tareas posteriores
        """
        phase_id = task.phase_id
        deleted_position = task.position

        # Eliminar la tarea
        db.delete(task)
        db.flush()  # Asegurar que el delete se ejecute antes de las actualizaciones

        # Actualizar posiciones de las tareas posteriores
        self.update_tasks_positions(
            db=db,
            phase_id=phase_id,  # type: ignore
            from_position=deleted_position + 1,  # type: ignore
            increment=-1,
        )

        db.commit()

    def move_task_to_phase(
        self,
        db: Session,
        task: Task,
        new_phase_id: int,
        new_position: Optional[int] = None,
    ) -> Task:
        """
        Mover una tarea a otra fase

        Args:
            db: Sesión de base de datos
            task: Tarea a mover
            new_phase_id: ID de la nueva fase
            new_position: Nueva posición (opcional, si no se especifica va al final)
        """
        old_phase_id = task.phase_id
        old_position = task.position

        # Si la nueva posición no se especifica, asignar al final de la nueva fase
        if new_position is None:
            new_position = (
                self.get_max_position_by_phase(db=db, phase_id=new_phase_id) + 1
            )

        # Actualizar posiciones en la fase origen (eliminar hueco)
        self.update_tasks_positions(
            db=db,
            phase_id=old_phase_id,  # type: ignore
            from_position=old_position + 1,  # type: ignore
            increment=-1,
        )

        # Hacer espacio en la fase destino
        self.update_tasks_positions(
            db=db,
            phase_id=new_phase_id,
            from_position=new_position,
            increment=1,
        )

        # Actualizar la tarea
        task.phase_id = new_phase_id  # type: ignore
        task.position = new_position  # type: ignore

        db.commit()
        db.refresh(task)
        return task


# Instancia global del repositorio
task_repository = TaskRepository()
