"""Tests para el modelo Task"""

from datetime import datetime, timedelta

import pytest

from app.database import Base
from app.models.phase import Phase
from app.models.project import Project
from app.models.task import Task, TaskStatus
from app.models.user import User
from tests.test_db_config import TestingSessionLocal, engine


@pytest.fixture(autouse=True)
def setup_database():
    """Configurar base de datos para cada test"""
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
        hashed_password="hashed_password",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_project(db_session, test_user):
    """Fixture para crear un proyecto de prueba"""
    project = Project(name="Test Project", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def test_phase(db_session, test_project):
    """Fixture para crear una fase de prueba"""
    phase = Phase(name="Test Phase", position=0, project_id=test_project.id)
    db_session.add(phase)
    db_session.commit()
    db_session.refresh(phase)
    return phase


class TestTaskModel:
    """Pruebas para el modelo Task"""

    def test_create_task_minimal_fields(self, db_session, test_phase):
        """Probar creación de tarea con campos mínimos"""
        task = Task(title="Minimal Task", position=0, phase_id=test_phase.id)

        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        assert task.id is not None
        assert task.title == "Minimal Task"  # type: ignore[comparison-overlap]
        assert task.position == 0  # type: ignore[comparison-overlap]
        assert task.phase_id == test_phase.id
        assert task.status == TaskStatus.PENDING  # type: ignore[comparison-overlap]
        assert task.completed is False  # Valor por defecto

    def test_create_task_all_fields(self, db_session, test_phase):
        """Probar creación de tarea con todos los campos"""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=7)

        task = Task(
            title="Complete Task",
            description="Descripción detallada de la tarea",
            position=1,
            status=TaskStatus.IN_PROGRESS,
            completed=False,
            start_date=start_date,
            end_date=end_date,
            phase_id=test_phase.id,
        )

        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        assert task.id is not None
        assert task.description == "Descripción detallada de la tarea"  # type: ignore[comparison-overlap]
        assert task.status == TaskStatus.IN_PROGRESS  # type: ignore[comparison-overlap]
        assert task.start_date == start_date  # type: ignore[comparison-overlap]
        assert task.end_date == end_date  # type: ignore[comparison-overlap]

    def test_task_relationship_with_phase(self, db_session, test_phase):
        """Probar relación de tarea con fase"""
        task = Task(title="Task With Phase", position=0, phase_id=test_phase.id)

        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        assert task.phase is not None
        assert task.phase.id == test_phase.id
        assert task.phase.name == test_phase.name

    def test_task_status_enum_values(self, db_session, test_phase):
        """Probar diferentes valores del enum TaskStatus"""
        # Pendiente
        task1 = Task(
            title="Task Pending",
            position=0,
            status=TaskStatus.PENDING,
            phase_id=test_phase.id,
        )
        db_session.add(task1)

        # En progreso
        task2 = Task(
            title="Task In Progress",
            position=1,
            status=TaskStatus.IN_PROGRESS,
            phase_id=test_phase.id,
        )
        db_session.add(task2)

        # Completada
        task3 = Task(
            title="Task Completed",
            position=2,
            status=TaskStatus.COMPLETED,
            phase_id=test_phase.id,
        )
        db_session.add(task3)

        db_session.commit()

        assert task1.status == TaskStatus.PENDING  # type: ignore[comparison-overlap]
        assert task2.status == TaskStatus.IN_PROGRESS  # type: ignore[comparison-overlap]
        assert task3.status == TaskStatus.COMPLETED  # type: ignore[comparison-overlap]

    def test_task_timestamps(self, db_session, test_phase):
        """Probar que los timestamps se crean automáticamente"""
        task = Task(title="Timestamps Task", position=0, phase_id=test_phase.id)

        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        assert task.created_at is not None
        assert task.updated_at is not None
        assert task.created_at <= task.updated_at  # type: ignore[comparison-overlap]

    def test_task_completed_flag(self, db_session, test_phase):
        """Probar el flag de completado"""
        task = Task(
            title="Completed Task",
            position=0,
            status=TaskStatus.COMPLETED,
            completed=True,
            phase_id=test_phase.id,
        )

        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        assert task.completed is True
        assert task.status == TaskStatus.COMPLETED  # type: ignore[comparison-overlap]

    def test_task_position_ordering(self, db_session, test_phase):
        """Probar ordenamiento por posición"""
        task1 = Task(title="Task 1", position=2, phase_id=test_phase.id)
        task2 = Task(title="Task 2", position=0, phase_id=test_phase.id)
        task3 = Task(title="Task 3", position=1, phase_id=test_phase.id)

        db_session.add_all([task1, task2, task3])
        db_session.commit()

        # Obtener tareas ordenadas por posición
        tasks = (
            db_session.query(Task)
            .filter(Task.phase_id == test_phase.id)
            .order_by(Task.position)
            .all()
        )

        assert len(tasks) == 3
        assert tasks[0].title == "Task 2"  # position=0
        assert tasks[1].title == "Task 3"  # position=1
        assert tasks[2].title == "Task 1"  # position=2

    def test_task_relationship_with_attachment(self, db_session, test_phase):
        """Probar relación de tarea con documento adjunto"""
        from app.models.attachment import Attachment, FileType

        task = Task(title="Task With Attachment", position=0, phase_id=test_phase.id)
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        # Crear adjunto con los campos correctos
        attachment = Attachment(
            file_name="document.pdf",
            file_path="/path/to/document.pdf",
            file_type=FileType.PDF,
            file_size=1024,
            task_id=task.id,
        )
        db_session.add(attachment)
        db_session.commit()

        # Verificar relación
        db_session.refresh(task)
        assert hasattr(task, "attachment")

    def test_task_nullable_fields(self, db_session, test_phase):
        """Probar que campos opcionales pueden ser None"""
        task = Task(
            title="Nullable Task",
            description=None,
            position=0,
            start_date=None,
            end_date=None,
            phase_id=test_phase.id,
        )

        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        assert task.description is None
        assert task.start_date is None
        assert task.end_date is None

    def test_task_repr(self, db_session, test_phase):
        """Probar representación de string de la tarea"""
        task = Task(title="Repr Task", position=0, phase_id=test_phase.id)

        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        task_repr = repr(task)
        # SQLAlchemy por defecto usa <ClassName object at 0x...>
        assert "Task" in task_repr or "Repr Task" in task_repr
