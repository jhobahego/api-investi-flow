import pytest
from fastapi import HTTPException

from app.database import Base
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskStatus, TaskUpdate
from app.services.task_service import task_service
from tests.test_db_config import TestingSessionLocal, engine


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Fixture para sesión de base de datos"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(db_session):
    """Fixture para crear un usuario de prueba"""
    user = User(
        email="testuser@example.com",
        full_name="Test User",
        hashed_password="Test123456",
        phone_number="+573001234567",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_project(db_session, test_user):
    """Fixture para crear un proyecto de prueba"""
    project = Project(
        name="Test Project",
        description="Test Description",
        owner_id=test_user.id,
        status="planning",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


# Hay que crear una fase para asignarla a la tarea
@pytest.fixture
def test_phase(db_session, test_project):
    """Fixture para crear una fase de prueba"""
    from app.models.phase import Phase

    phase = Phase(
        name="Test Phase",
        position=0,
        color="#FF5733",
        project_id=test_project.id,
    )
    db_session.add(phase)
    db_session.commit()
    db_session.refresh(phase)
    return phase


@pytest.fixture
def test_task(db_session, test_phase):
    """Fixture para crear una tarea de prueba"""
    task = Task(
        title="Test Task",
        description="Test Task Description",
        position=0,
        status=TaskStatus.PENDING,
        phase_id=test_phase.id,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


class TestTaskService:
    """Pruebas para el servicio de tareas"""

    def test_create_task_success(self, db_session, test_user, test_phase):
        """Probar creación exitosa de tarea"""
        task_data = TaskCreate(
            title="Nueva Tarea",
            description="Descripción de la nueva tarea",
            position=0,
            phase_id=test_phase.id,
            start_date=None,
            end_date=None,
            status=TaskStatus.PENDING,
            completed=False,
        )

        result = task_service.create_task(
            db=db_session,
            task_in=task_data,
            owner_id=test_user.id,
        )

        assert result is not None
        assert result.title == "Nueva Tarea"  # type: ignore
        assert result.description == "Descripción de la nueva tarea"  # type: ignore
        assert result.position == 0  # type: ignore
        assert result.phase_id == test_phase.id

    def test_create_task_phase_not_found(self, db_session, test_user):
        """Probar creación de tarea con fase inválida"""
        task_data = TaskCreate(
            title="Tarea Inválida",
            description="Descripción de la tarea inválida",
            position=0,
            phase_id=9999,  # ID de fase que no existe
            start_date=None,
            end_date=None,
            status=TaskStatus.PENDING,
            completed=False,
        )

        with pytest.raises(HTTPException) as exc_info:
            task_service.create_task(
                db=db_session,
                task_in=task_data,
                owner_id=test_user.id,
            )

        assert exc_info.value.status_code == 404
        assert "Fase no encontrada" in exc_info.value.detail

    def test_get_task_success(self, db_session, test_user, test_task):
        """Probar obtención exitosa de tarea"""
        result = task_service.get_task_by_id(
            db=db_session,
            task_id=test_task.id,
            owner_id=test_user.id,
        )

        assert result is not None
        assert result.id == test_task.id
        assert result.title == test_task.title

    def test_get_task_not_found(self, db_session, test_user):
        """Probar obtención de tarea que no existe"""
        with pytest.raises(HTTPException) as exc_info:
            task_service.get_task_by_id(
                db=db_session,
                task_id=9999,  # ID de tarea que no existe
                owner_id=test_user.id,
            )

        assert exc_info.value.status_code == 404
        assert "Tarea no encontrada" in exc_info.value.detail

    def test_update_task_success(self, db_session, test_user, test_task):
        """Probar actualización exitosa de tarea"""
        update_data = TaskUpdate(
            title="Tarea Actualizada",
            description="Descripción de la tarea actualizada",
            position=1,
            status=TaskStatus.IN_PROGRESS,
            start_date=None,
            end_date=None,
            completed=False,
        )
        result = task_service.update_task(
            db=db_session,
            task_id=test_task.id,
            task_in=update_data,
            owner_id=test_user.id,
        )
        assert result is not None
        assert result.id == test_task.id
        assert result.title == "Tarea Actualizada"  # type: ignore
        assert result.description == "Descripción de la tarea actualizada"  # type: ignore
        assert result.position == 1  # type: ignore

    def test_update_task_not_found(self, db_session, test_user):
        """Probar actualización de tarea que no existe"""
        update_data = TaskUpdate(
            title="Tarea Inexistente",
            description="Descripción de la tarea inexistente",
            position=1,
            start_date=None,
            end_date=None,
            status=TaskStatus.IN_PROGRESS,
            completed=False,
        )

        with pytest.raises(HTTPException) as exc_info:
            task_service.update_task(
                db=db_session,
                task_id=9999,  # ID de tarea que no existe
                task_in=update_data,
                owner_id=test_user.id,
            )

        assert exc_info.value.status_code == 404
        assert "Tarea no encontrada" in exc_info.value.detail

    # def update_task(
    #     self, db: Session, task_id: int, task_in: TaskUpdate, owner_id: int
    # ) -> Task:
    #     """
    #     Actualizar una tarea.

    #     Args:
    #         db: Sesión de base de datos
    #         task_id: ID de la tarea
    #         task_in: Datos a actualizar
    #         owner_id: ID del usuario propietario

    #     Returns:
    #         Tarea actualizada

    #     Raises:
    #         HTTPException: Si la tarea no existe o no pertenece al usuario
    #     """
    #     # Verificar que la tarea existe y pertenece al usuario
    #     task = self.get_task_by_id(db=db, task_id=task_id, owner_id=owner_id)

    #     try:
    #         # Si se está actualizando la posición dentro de la misma fase
    #         if task_in.position is not None and task_in.position != task.position:
    #             old_position = task.position
    #             new_position = task_in.position

    #             # Verificar si ya existe una tarea en la nueva posición
    #             existing_task = task_repository.get_task_by_phase_and_position(
    #                 db=db,
    #                 phase_id=task.phase_id,  # type: ignore
    #                 position=new_position,
    #             )

    #             if existing_task and existing_task.id != task.id:  # type: ignore
    #                 if new_position < old_position:  # type: ignore
    #                     # Mover hacia arriba: incrementar posiciones entre new_position y old_position-1
    #                     tasks_to_update = (
    #                         db.query(Task)
    #                         .filter(
    #                             Task.phase_id == task.phase_id,
    #                             Task.position >= new_position,
    #                             Task.position < old_position,
    #                             Task.id != task.id,
    #                         )
    #                         .all()
    #                     )
    #                     for t in tasks_to_update:
    #                         setattr(t, "position", t.position + 1)
    #                 else:
    #                     # Mover hacia abajo: decrementar posiciones entre old_position+1 y new_position
    #                     tasks_to_update = (
    #                         db.query(Task)
    #                         .filter(
    #                             Task.phase_id == task.phase_id,
    #                             Task.position > old_position,
    #                             Task.position <= new_position,
    #                             Task.id != task.id,
    #                         )
    #                         .all()
    #                     )
    #                     for t in tasks_to_update:
    #                         setattr(t, "position", t.position - 1)

    #                 db.flush()  # Aplicar cambios antes de actualizar la tarea actual

    #         # Actualizar la tarea
    #         updated_task = task_repository.update_task(
    #             db=db, task=task, task_in=task_in
    #         )
    #         return updated_task

    #     except HTTPException:
    #         raise
    #     except Exception as e:
    #         db.rollback()
    #         raise HTTPException(
    #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #             detail=f"Error al actualizar la tarea: {str(e)}",
    #         )

    # def delete_task(self, db: Session, task_id: int, owner_id: int) -> bool:
    #     """
    #     Eliminar una tarea.

    #     Args:
    #         db: Sesión de base de datos
    #         task_id: ID de la tarea
    #         owner_id: ID del usuario propietario

    #     Returns:
    #         True si se eliminó correctamente

    #     Raises:
    #         HTTPException: Si la tarea no existe o no pertenece al usuario
    #     """
    #     # Verificar que la tarea existe y pertenece al usuario
    #     task = self.get_task_by_id(db=db, task_id=task_id, owner_id=owner_id)

    #     try:
    #         # Eliminar la tarea y actualizar posiciones
    #         task_repository.delete_task_and_update_positions(db=db, task=task)
    #         return True

    #     except Exception as e:
    #         db.rollback()
    #         raise HTTPException(
    #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #             detail=f"Error al eliminar la tarea: {str(e)}",
    #         )

    # def move_task_to_phase(
    #     self,
    #     db: Session,
    #     task_id: int,
    #     new_phase_id: int,
    #     new_position: Optional[int],
    #     owner_id: int,
    # ) -> Task:
    #     """
    #     Mover una tarea a otra fase.

    #     Args:
    #         db: Sesión de base de datos
    #         task_id: ID de la tarea
    #         new_phase_id: ID de la nueva fase
    #         new_position: Nueva posición (opcional)
    #         owner_id: ID del usuario propietario

    #     Returns:
    #         Tarea actualizada

    #     Raises:
    #         HTTPException: Si la tarea o fase no existen o no pertenecen al usuario
    #     """
    #     # Verificar que la tarea existe y pertenece al usuario
    #     task = self.get_task_by_id(db=db, task_id=task_id, owner_id=owner_id)

    #     # Verificar que la nueva fase existe y pertenece a un proyecto del usuario
    #     new_phase = phase_repository.get(db=db, id=new_phase_id)
    #     if not new_phase:
    #         raise HTTPException(
    #             status_code=status.HTTP_404_NOT_FOUND,
    #             detail="Fase destino no encontrada",
    #         )

    #     # Verificar que el proyecto de la nueva fase pertenece al usuario
    #     project = project_repository.get_project_by_owner_and_id(
    #         db=db,
    #         project_id=new_phase.project_id,  # type: ignore
    #         owner_id=owner_id,
    #     )
    #     if not project:
    #         raise HTTPException(
    #             status_code=status.HTTP_404_NOT_FOUND,
    #             detail="No tienes permisos para mover la tarea a esta fase",
    #         )

    #     try:
    #         # Mover la tarea a la nueva fase
    #         updated_task = task_repository.move_task_to_phase(
    #             db=db, task=task, new_phase_id=new_phase_id, new_position=new_position
    #         )
    #         return updated_task

    #     except Exception as e:
    #         db.rollback()
    #         raise HTTPException(
    #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #             detail=f"Error al mover la tarea: {str(e)}",
    #         )

    # def reorder_tasks_in_phase(
    #     self, db: Session, phase_id: int, task_orders: List[dict], owner_id: int
    # ) -> List[Task]:
    #     """
    #     Reordenar las tareas de una fase.

    #     Args:
    #         db: Sesión de base de datos
    #         phase_id: ID de la fase
    #         task_orders: Lista de diccionarios con id y position de cada tarea
    #         owner_id: ID del usuario propietario

    #     Returns:
    #         Lista de tareas reordenadas

    #     Raises:
    #         HTTPException: Si hay error en la validación o reordenamiento
    #     """
    #     try:
    #         # Verificar que la fase existe y pertenece a un proyecto del usuario
    #         phase = phase_repository.get(db=db, id=phase_id)
    #         if not phase:
    #             raise HTTPException(
    #                 status_code=status.HTTP_404_NOT_FOUND,
    #                 detail="Fase no encontrada",
    #             )

    #         # Verificar que el proyecto de la fase pertenece al usuario
    #         project = project_repository.get_project_by_owner_and_id(
    #             db=db,
    #             project_id=phase.project_id,  # type: ignore
    #             owner_id=owner_id,
    #         )
    #         if not project:
    #             raise HTTPException(
    #                 status_code=status.HTTP_404_NOT_FOUND,
    #                 detail="No tienes permisos para reordenar las tareas de esta fase",
    #             )

    #         # Obtener todas las tareas de la fase
    #         tasks = task_repository.get_tasks_by_phase(db=db, phase_id=phase_id)
    #         task_dict = {task.id: task for task in tasks}

    #         # Validar que todas las tareas en task_orders existen
    #         for order in task_orders:
    #             task_id = order.get("id")
    #             if task_id not in task_dict:
    #                 raise HTTPException(
    #                     status_code=status.HTTP_400_BAD_REQUEST,
    #                     detail=f"Tarea con ID {task_id} no encontrada en la fase",
    #                 )

    #         # Actualizar las posiciones
    def test_delete_task_success(self, db_session, test_user, test_task):
        """Probar eliminación exitosa de tarea"""
        result = task_service.delete_task(
            db=db_session,
            task_id=test_task.id,
            owner_id=test_user.id,
        )
        assert result is True

        # Verificar que la tarea ya no existe
        with pytest.raises(HTTPException) as exc_info:
            task_service.get_task_by_id(
                db=db_session,
                task_id=test_task.id,
                owner_id=test_user.id,
            )

        assert exc_info.value.status_code == 404
        assert "Tarea no encontrada" in exc_info.value.detail

    def test_delete_task_not_found(self, db_session, test_user):
        """Probar eliminación de tarea que no existe"""
        with pytest.raises(HTTPException) as exc_info:
            task_service.delete_task(
                db=db_session,
                task_id=9999,  # ID de tarea que no existe
                owner_id=test_user.id,
            )

        assert exc_info.value.status_code == 404
        assert "Tarea no encontrada" in exc_info.value.detail

    def test_move_task_to_phase_success(self, db_session, test_user, test_task):
        """Probar mover tarea a otra fase exitosamente"""
        # Crear una nueva fase para mover la tarea
        from app.models.phase import Phase

        new_phase = Phase(
            name="Nueva Fase",
            position=1,
            color="#33FF57",
            project_id=test_task.phase.project_id,  # type: ignore
        )
        db_session.add(new_phase)
        db_session.commit()
        db_session.refresh(new_phase)

        result = task_service.move_task_to_phase(
            db=db_session,
            task_id=test_task.id,
            new_phase_id=new_phase.id,  # type: ignore
            new_position=0,
            owner_id=test_user.id,
        )

        assert result is not None
        assert result.id == test_task.id
        assert result.phase_id == new_phase.id  # type: ignore
        assert result.position == 0  # type: ignore

    def test_move_task_to_phase_not_found(self, db_session, test_user, test_task):
        """Probar mover tarea a fase que no existe"""
        with pytest.raises(HTTPException) as exc_info:
            task_service.move_task_to_phase(
                db=db_session,
                task_id=test_task.id,
                new_phase_id=9999,  # ID de fase que no existe
                new_position=0,
                owner_id=test_user.id,
            )

        assert exc_info.value.status_code == 404
        assert "Fase destino no encontrada" in exc_info.value.detail

    def test_reorder_tasks_in_phase_success(self, db_session, test_user, test_task):
        """Probar reordenar tareas en una fase exitosamente"""
        # Crear tareas adicionales en la fase
        task1 = Task(
            title="Tarea 1",
            description="Descripción de la tarea 1",
            position=1,
            status=TaskStatus.PENDING,
            phase_id=test_task.phase_id,
        )
        task2 = Task(
            title="Tarea 2",
            description="Descripción de la tarea 2",
            position=2,
            status=TaskStatus.PENDING,
            phase_id=test_task.phase_id,
        )
        db_session.add_all([task1, task2])
        db_session.commit()
        db_session.refresh(task1)
        db_session.refresh(task2)

        # Nuevo orden: task2 en posición 0, test_task en posición 1, task1 en posición 2
        task_orders = [
            {"id": task2.id, "position": 0},  # type: ignore
            {"id": test_task.id, "position": 1},  # type: ignore
            {"id": task1.id, "position": 2},  # type: ignore
        ]

        result = task_service.reorder_tasks_in_phase(
            db=db_session,
            phase_id=test_task.phase_id,
            task_orders=task_orders,
            owner_id=test_user.id,
        )

        assert result is not None
        assert len(result) == 3
        assert result[0].id == task2.id  # type: ignore
        assert result[1].id == test_task.id  # type: ignore
        assert result[2].id == task1.id  # type: ignore

    def test_reorder_tasks_in_phase_not_found(self, db_session, test_user):
        """Probar reordenar tareas en fase que no existe"""
        task_orders = [{"id": 1, "position": 0}]

        with pytest.raises(HTTPException) as exc_info:
            task_service.reorder_tasks_in_phase(
                db=db_session,
                phase_id=9999,  # ID de fase que no existe
                task_orders=task_orders,
                owner_id=test_user.id,
            )
        assert exc_info.value.status_code == 404
        assert "Fase no encontrada" in exc_info.value.detail
        # assert "no encontrada" in exc_info.value.detail --- IGNORE ---

    def test_reorder_tasks_in_phase_invalid_task(
        self, db_session, test_user, test_phase
    ):
        """Probar reordenar tareas con tarea que no existe en la fase"""
        task_orders = [{"id": 9999, "position": 0}]
        with pytest.raises(HTTPException) as exc_info:
            task_service.reorder_tasks_in_phase(
                db=db_session,
                phase_id=test_phase.id,
                task_orders=task_orders,
                owner_id=test_user.id,
            )
        assert exc_info.value.status_code == 400
        assert "Tarea con ID 9999 no encontrada en la fase" in exc_info.value.detail
        # assert "no encontrada" in exc_info.value.detail --- IGNORE ---
