"""
Configuración global de fixtures para pytest.

Este archivo contiene fixtures que están disponibles para todos los tests
sin necesidad de importarlos explícitamente.
"""

from typing import Generator

import pytest
from sqlalchemy.orm import Session

from app.database import Base
from app.models.phase import Phase
from app.models.project import Project
from app.models.task import Task, TaskStatus
from app.models.user import User
from tests.test_db_config import TestingSessionLocal, engine


@pytest.fixture(scope="function", autouse=True)
def reset_database():
    """
    Fixture para resetear la base de datos antes de cada test.
    Se ejecuta automáticamente para todos los tests.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Fixture para proporcionar una sesión de base de datos para los tests.

    Yields:
        Session: Sesión de SQLAlchemy para interactuar con la base de datos de prueba
    """
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(db_session: Session) -> User:
    """
    Fixture para crear un usuario de prueba estándar.

    Args:
        db_session: Sesión de base de datos

    Returns:
        User: Usuario de prueba creado
    """
    user = User(
        email="testuser@example.com",
        full_name="Test User",
        hashed_password="hashed_test_password",
        phone_number="+573001234567",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_superuser(db_session: Session) -> User:
    """
    Fixture para crear un superusuario de prueba.

    Args:
        db_session: Sesión de base de datos

    Returns:
        User: Superusuario de prueba creado
    """
    user = User(
        email="admin@example.com",
        full_name="Admin User",
        hashed_password="hashed_admin_password",
        phone_number="+573009999999",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_project(db_session: Session, test_user: User) -> Project:
    """
    Fixture para crear un proyecto de prueba.

    Args:
        db_session: Sesión de base de datos
        test_user: Usuario propietario del proyecto

    Returns:
        Project: Proyecto de prueba creado
    """
    project = Project(
        name="Test Project",
        description="Test project description",
        research_type="experimental",
        institution="Test University",
        status="planning",
        owner_id=test_user.id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def test_phase(db_session: Session, test_project: Project) -> Phase:
    """
    Fixture para crear una fase de prueba.

    Args:
        db_session: Sesión de base de datos
        test_project: Proyecto al que pertenece la fase

    Returns:
        Phase: Fase de prueba creada
    """
    phase = Phase(
        name="Test Phase",
        description="Test phase description",
        position=0,
        color="#FF5733",
        project_id=test_project.id,
    )
    db_session.add(phase)
    db_session.commit()
    db_session.refresh(phase)
    return phase


@pytest.fixture
def test_task(db_session: Session, test_phase: Phase) -> Task:
    """
    Fixture para crear una tarea de prueba.

    Args:
        db_session: Sesión de base de datos
        test_phase: Fase a la que pertenece la tarea

    Returns:
        Task: Tarea de prueba creada
    """
    task = Task(
        title="Test Task",
        description="Test task description",
        position=0,
        status=TaskStatus.PENDING,
        completed=False,
        phase_id=test_phase.id,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture
def multiple_users(db_session: Session) -> list[User]:
    """
    Fixture para crear múltiples usuarios de prueba.

    Args:
        db_session: Sesión de base de datos

    Returns:
        list[User]: Lista de usuarios de prueba creados
    """
    users = []
    for i in range(3):
        user = User(
            email=f"user{i}@example.com",
            full_name=f"User {i}",
            hashed_password=f"hashed_password_{i}",
            phone_number=f"+57300123456{i}",
            is_active=True,
        )
        db_session.add(user)
        users.append(user)

    db_session.commit()
    for user in users:
        db_session.refresh(user)

    return users


@pytest.fixture
def multiple_projects(db_session: Session, test_user: User) -> list[Project]:
    """
    Fixture para crear múltiples proyectos de prueba.

    Args:
        db_session: Sesión de base de datos
        test_user: Usuario propietario de los proyectos

    Returns:
        list[Project]: Lista de proyectos de prueba creados
    """
    projects = []
    for i in range(3):
        project = Project(
            name=f"Project {i}",
            description=f"Description for project {i}",
            status="planning",
            owner_id=test_user.id,
        )
        db_session.add(project)
        projects.append(project)

    db_session.commit()
    for project in projects:
        db_session.refresh(project)

    return projects


@pytest.fixture
def multiple_phases(db_session: Session, test_project: Project) -> list[Phase]:
    """
    Fixture para crear múltiples fases de prueba.

    Args:
        db_session: Sesión de base de datos
        test_project: Proyecto al que pertenecen las fases

    Returns:
        list[Phase]: Lista de fases de prueba creadas
    """
    phases = []
    colors = ["#FF5733", "#33FF57", "#3357FF"]

    for i, color in enumerate(colors):
        phase = Phase(
            name=f"Phase {i}",
            position=i,
            color=color,
            project_id=test_project.id,
        )
        db_session.add(phase)
        phases.append(phase)

    db_session.commit()
    for phase in phases:
        db_session.refresh(phase)

    return phases


@pytest.fixture
def multiple_tasks(db_session: Session, test_phase: Phase) -> list[Task]:
    """
    Fixture para crear múltiples tareas de prueba.

    Args:
        db_session: Sesión de base de datos
        test_phase: Fase a la que pertenecen las tareas

    Returns:
        list[Task]: Lista de tareas de prueba creadas
    """
    tasks = []
    statuses = [TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED]

    for i, status in enumerate(statuses):
        task = Task(
            title=f"Task {i}",
            description=f"Description for task {i}",
            position=i,
            status=status,
            completed=(status == TaskStatus.COMPLETED),
            phase_id=test_phase.id,
        )
        db_session.add(task)
        tasks.append(task)

    db_session.commit()
    for task in tasks:
        db_session.refresh(task)

    return tasks
