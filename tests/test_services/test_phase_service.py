import pytest
from fastapi import HTTPException

from app.database import Base
from app.models.phase import Phase
from app.models.project import Project
from app.models.user import User
from app.schemas.phase import PhaseCreate, PhaseUpdate
from app.services.phase_service import phase_service
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
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password",
        phone_number="+573001234567",
        is_active=True,
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


@pytest.fixture
def test_phase(db_session, test_project):
    """Fixture para crear una fase de prueba"""
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


class TestPhaseService:
    """Pruebas para el servicio de fases"""

    def test_create_phase_success(self, db_session, test_user, test_project):
        """Probar creación exitosa de fase"""
        phase_data = PhaseCreate(
            name="Nueva Fase",
            position=0,
            project_id=test_project.id,
            color=None,
        )

        result = phase_service.create_phase(
            db=db_session,
            phase_in=phase_data,
            owner_id=test_user.id,
        )

        assert result is not None
        assert result.name == "Nueva Fase"  # type: ignore
        assert result.position == 0  # type: ignore
        assert result.project_id == test_project.id

    def test_create_phase_project_not_found(self, db_session, test_user):
        """Probar creación de fase con proyecto inexistente"""
        phase_data = PhaseCreate(
            name="Fase Sin Proyecto",
            position=0,
            project_id=999999,
            color=None,
        )

        with pytest.raises(HTTPException) as exc_info:
            phase_service.create_phase(
                db=db_session,
                phase_in=phase_data,
                owner_id=test_user.id,
            )

        assert exc_info.value.status_code == 404
        assert (
            "Proyecto no encontrado o no tienes permisos para acceder a él"
            in exc_info.value.detail
        )

    def test_get_phase_by_id_success(self, db_session, test_user, test_phase):
        """Probar obtener fase por ID exitosamente"""
        result = phase_service.get_phase_by_id(
            db=db_session,
            phase_id=test_phase.id,
            owner_id=test_user.id,
        )

        assert result is not None
        assert result.id == test_phase.id

    def test_get_phase_by_id_not_found(self, db_session, test_user):
        """Probar obtener fase inexistente"""
        with pytest.raises(HTTPException) as exc_info:
            phase_service.get_phase_by_id(
                db=db_session,
                phase_id=999999,
                owner_id=test_user.id,
            )

        assert exc_info.value.status_code == 404
        assert "Fase no encontrada" in exc_info.value.detail

    def test_update_phase_success(self, db_session, test_user, test_phase):
        """Probar actualización exitosa de fase"""
        update_data = PhaseUpdate(name="Fase Actualizada", color="#FFFFFF", position=1)

        result = phase_service.update_phase(
            db=db_session,
            phase_id=test_phase.id,
            phase_in=update_data,
            owner_id=test_user.id,
        )

        assert result is not None
        assert result.id == test_phase.id
        assert result.name == "Fase Actualizada"  # type: ignore
        assert result.color == "#FFFFFF"  # type: ignore
        assert result.position == 1  # type: ignore

    def test_update_phase_not_found(self, db_session, test_user):
        """Probar actualización de fase inexistente"""
        update_data = PhaseUpdate(name="Fase Inexistente", color="#000000", position=2)

        with pytest.raises(HTTPException) as exc_info:
            phase_service.update_phase(
                db=db_session,
                phase_id=999999,
                phase_in=update_data,
                owner_id=test_user.id,
            )

        assert exc_info.value.status_code == 404
        assert "Fase no encontrada" in exc_info.value.detail

    def test_delete_phase_success(self, db_session, test_user, test_phase):
        """Probar eliminación exitosa de fase"""
        phase_id = test_phase.id

        result = phase_service.delete_phase(
            db=db_session,
            phase_id=phase_id,
            owner_id=test_user.id,
        )

        assert result is True

        # Verificar que la fase fue eliminada
        deleted_phase = db_session.query(Phase).filter(Phase.id == phase_id).first()
        assert deleted_phase is None

    def test_delete_phase_not_found(self, db_session, test_user):
        """Probar eliminación de fase inexistente"""
        with pytest.raises(HTTPException) as exc_info:
            phase_service.delete_phase(
                db=db_session,
                phase_id=999999,
                owner_id=test_user.id,
            )

        assert exc_info.value.status_code == 404
        assert "Fase no encontrada" in exc_info.value.detail

    def test_reorder_phases_success(self, db_session, test_user, test_project):
        """Probar reordenamiento exitoso de fases"""
        # Crear tres fases
        phases = []
        for i in range(3):
            phase_data = PhaseCreate(
                name=f"Fase {i + 1}",
                position=i,
                project_id=test_project.id,
                color=None,
            )
            phase = phase_service.create_phase(
                db=db_session,
                phase_in=phase_data,
                owner_id=test_user.id,
            )
            phases.append(phase)

        # Reordenar fases
        phase_orders = [
            {"id": phases[2].id, "position": 0},
            {"id": phases[0].id, "position": 1},
            {"id": phases[1].id, "position": 2},
        ]

        result = phase_service.reorder_phases(
            db=db_session,
            project_id=test_project.id,
            phase_orders=phase_orders,
            owner_id=test_user.id,
        )

        assert len(result) == 3

    def test_reorder_phases_project_not_found(self, db_session, test_user):
        """Probar reordenamiento con proyecto inexistente"""
        phase_orders = [{"id": 1, "position": 0}]

        with pytest.raises(HTTPException) as exc_info:
            phase_service.reorder_phases(
                db=db_session,
                project_id=999999,
                phase_orders=phase_orders,
                owner_id=test_user.id,
            )

        assert exc_info.value.status_code == 404
        assert (
            "Proyecto no encontrado o no tienes permisos para acceder a él"
            in exc_info.value.detail
        )

    def test_get_phase_tasks(self, db_session, test_user, test_phase):
        """Probar obtener tareas de una fase"""
        result = phase_service.get_phase_tasks(
            db=db_session,
            phase_id=test_phase.id,
        )

        # El resultado debe ser una lista (aunque esté vacía)
        assert isinstance(result, list)

    def test_get_phase_tasks_phase_not_found(self, db_session):
        """Probar obtener tareas de fase inexistente"""
        with pytest.raises(HTTPException) as exc_info:
            phase_service.get_phase_tasks(
                db=db_session,
                phase_id=999999,
            )

        assert exc_info.value.status_code == 404
        assert "Fase no encontrada" in exc_info.value.detail
