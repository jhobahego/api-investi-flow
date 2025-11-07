"""Tests para el modelo Project"""

import pytest

from app.database import Base
from app.models.project import Project
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


class TestProjectModel:
    """Pruebas para el modelo Project"""

    def test_create_project_minimal_fields(self, db_session, test_user):
        """Probar creación de proyecto con campos mínimos"""
        project = Project(name="Minimal Project", owner_id=test_user.id)

        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        assert project.id is not None
        assert project.name == "Minimal Project"  # type: ignore[comparison-overlap]
        assert project.owner_id == test_user.id
        assert project.status == "planning"  # type: ignore[comparison-overlap]

    def test_create_project_all_fields(self, db_session, test_user):
        """Probar creación de proyecto con todos los campos"""
        project = Project(
            name="Complete Project",
            description="Descripción detallada",
            research_type="experimental",
            institution="Universidad Test",
            research_group="Grupo Test",
            category="Tecnología",
            status="in_progress",
            owner_id=test_user.id,
        )

        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        assert project.id is not None
        assert project.description == "Descripción detallada"  # type: ignore[comparison-overlap]
        assert project.research_type == "experimental"  # type: ignore[comparison-overlap]
        assert project.institution == "Universidad Test"  # type: ignore[comparison-overlap]
        assert project.research_group == "Grupo Test"  # type: ignore[comparison-overlap]
        assert project.category == "Tecnología"  # type: ignore[comparison-overlap]
        assert project.status == "in_progress"  # type: ignore[comparison-overlap]

    def test_project_relationship_with_owner(self, db_session, test_user):
        """Probar relación de proyecto con propietario"""
        project = Project(name="Test Project", owner_id=test_user.id)

        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        assert project.owner is not None
        assert project.owner.id == test_user.id
        assert project.owner.email == test_user.email

    def test_project_relationship_with_phases(self, db_session, test_user):
        """Probar relación de proyecto con fases"""
        from app.models.phase import Phase

        project = Project(name="Project With Phases", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # Crear fases
        phase1 = Phase(name="Fase 1", position=0, project_id=project.id)
        phase2 = Phase(name="Fase 2", position=1, project_id=project.id)

        db_session.add_all([phase1, phase2])
        db_session.commit()

        # Verificar relación
        db_session.refresh(project)
        assert len(project.phases) == 2  # type: ignore
        assert phase1 in project.phases  # type: ignore
        assert phase2 in project.phases  # type: ignore

    def test_project_default_status(self, db_session, test_user):
        """Probar que el status por defecto es 'planning'"""
        project = Project(name="Default Status Project", owner_id=test_user.id)

        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        assert project.status == "planning"  # type: ignore[comparison-overlap]

    def test_project_timestamps(self, db_session, test_user):
        """Probar que los timestamps se crean automáticamente"""
        project = Project(name="Timestamps Project", owner_id=test_user.id)

        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        assert project.created_at is not None
        assert project.updated_at is not None
        assert project.created_at <= project.updated_at  # type: ignore[comparison-overlap]

    def test_project_cascade_delete_phases(self, db_session, test_user):
        """Probar eliminación en cascada de fases al eliminar proyecto"""
        from app.models.phase import Phase

        project = Project(name="Cascade Project", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # Crear fase
        phase = Phase(name="Fase a eliminar", position=0, project_id=project.id)
        db_session.add(phase)
        db_session.commit()
        phase_id = phase.id

        # Eliminar proyecto
        db_session.delete(project)
        db_session.commit()

        # Verificar que la fase fue eliminada
        deleted_phase = db_session.query(Phase).filter(Phase.id == phase_id).first()
        assert deleted_phase is None

    def test_project_repr(self, db_session, test_user):
        """Probar representación de string del proyecto"""
        project = Project(name="Repr Project", owner_id=test_user.id)

        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        project_repr = repr(project)
        # SQLAlchemy por defecto usa <ClassName object at 0x...>
        assert "Project" in project_repr or "Repr Project" in project_repr

    def test_project_nullable_fields(self, db_session, test_user):
        """Probar que campos opcionales pueden ser None"""
        project = Project(
            name="Nullable Project",
            description=None,
            research_type=None,
            institution=None,
            research_group=None,
            category=None,
            owner_id=test_user.id,
        )

        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        assert project.description is None
        assert project.research_type is None
        assert project.institution is None
        assert project.research_group is None
        assert project.category is None
