"""Tests para el servicio de proyectos"""

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.database import Base
from app.models.project import Project, ProjectStatus, ResearchType
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.project_service import project_service
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


class TestProjectService:
    """Pruebas para el servicio de proyectos"""

    def test_create_project_success(self, db_session, test_user):
        """Probar creación exitosa de proyecto"""
        project_data = ProjectCreate(
            name="Nuevo Proyecto",
            description="Descripción del proyecto",
            research_type=ResearchType.EXPERIMENTAL,
            institution="Universidad Test",
            research_group="Grupo Test",
            category="Tecnología",
            status=ProjectStatus.PLANNING,
        )

        result = project_service.create_project(
            db=db_session, project_in=project_data, owner_id=test_user.id
        )

        assert result is not None
        assert result.name == "Nuevo Proyecto"  # type: ignore[comparison-overlap]
        assert result.description == "Descripción del proyecto"  # type: ignore[comparison-overlap]
        assert result.research_type == "experimental"  # type: ignore[comparison-overlap]
        assert result.institution == "Universidad Test"  # type: ignore[comparison-overlap]
        assert result.owner_id == test_user.id

    def test_create_project_empty_name(self, db_session, test_user):
        """Probar creación de proyecto con nombre vacío"""
        # Pydantic valida antes de llegar al servicio
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreate(
                name="",
                description="Descripción",
                research_group="Grupo de Investigación",
                research_type=ResearchType.EXPERIMENTAL,
                institution="Institución",
                category="Categoría",
                status=ProjectStatus.PLANNING,
            )

        assert "string_too_short" in str(exc_info.value)

    def test_create_project_whitespace_name(self, db_session, test_user):
        """Probar creación de proyecto con nombre de solo espacios"""
        # Pydantic valida antes de llegar al servicio
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreate(
                name="   ",
                description="Descripción",
                research_group="Grupo de Investigación",
                research_type=ResearchType.EXPERIMENTAL,
                institution="Institución",
                category="Categoría",
                status=ProjectStatus.PLANNING,
            )

        assert "nombre del proyecto no puede estar vacío" in str(exc_info.value).lower()

    def test_get_user_projects_empty(self, db_session, test_user):
        """Probar obtener proyectos cuando el usuario no tiene ninguno"""
        result = project_service.get_user_projects(db=db_session, owner_id=test_user.id)

        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_user_projects_multiple(self, db_session, test_user):
        """Probar obtener múltiples proyectos del usuario"""
        # Crear varios proyectos
        projects = []
        for i in range(3):
            project = Project(
                name=f"Proyecto {i + 1}",
                description=f"Descripción {i + 1}",
                owner_id=test_user.id,
                status="planning",
            )
            db_session.add(project)
            projects.append(project)

        db_session.commit()

        result = project_service.get_user_projects(db=db_session, owner_id=test_user.id)

        assert isinstance(result, list)
        assert len(result) == 3

    def test_get_user_project_by_id_success(self, db_session, test_user, test_project):
        """Probar obtener proyecto específico del usuario exitosamente"""
        result = project_service.get_user_project_by_id(
            db=db_session, project_id=test_project.id, owner_id=test_user.id
        )

        assert result is not None
        assert result.id == test_project.id
        assert result.name == test_project.name

    def test_get_user_project_by_id_not_found(self, db_session, test_user):
        """Probar obtener proyecto que no existe"""
        with pytest.raises(HTTPException) as exc_info:
            project_service.get_user_project_by_id(
                db=db_session, project_id=99999, owner_id=test_user.id
            )

        assert exc_info.value.status_code == 404
        assert "Proyecto no encontrado" in exc_info.value.detail

    def test_get_user_project_by_id_wrong_owner(self, db_session, test_project):
        """Probar obtener proyecto de otro usuario"""
        # Crear otro usuario
        other_user = User(
            email="otheruser@example.com",
            full_name="Other User",
            hashed_password="hashed_password",
            phone_number="+573009876543",
            is_active=True,
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        with pytest.raises(HTTPException) as exc_info:
            project_service.get_user_project_by_id(
                db=db_session,
                project_id=test_project.id,
                owner_id=other_user.id,  # type: ignore[arg-type]
            )

        assert exc_info.value.status_code == 404
        assert "Proyecto no encontrado" in exc_info.value.detail

    def test_update_user_project_success(self, db_session, test_user, test_project):
        """Probar actualización exitosa de proyecto"""
        update_data = ProjectUpdate(
            name="Proyecto Actualizado",
            description="Descripción actualizada",
            research_group="Grupo de Investigación",
            research_type=ResearchType.EXPERIMENTAL,
            institution="Institución",
            category="Categoría",
            status=ProjectStatus.IN_PROGRESS,
        )

        result = project_service.update_user_project(
            db=db_session,
            project_id=test_project.id,
            project_in=update_data,
            owner_id=test_user.id,
        )

        assert result is not None
        assert result.id == test_project.id
        assert result.name == "Proyecto Actualizado"  # type: ignore[comparison-overlap]
        assert result.description == "Descripción actualizada"  # type: ignore[comparison-overlap]
        assert result.status == "in_progress"  # type: ignore[comparison-overlap]

    def test_update_user_project_not_found(self, db_session, test_user):
        """Probar actualización de proyecto que no existe"""
        update_data = ProjectUpdate(
            name="Proyecto Inexistente",
            description="Descripción",
            research_group="Grupo de Investigación",
            research_type=ResearchType.EXPERIMENTAL,
            institution="Institución",
            category="Categoría",
            status=ProjectStatus.PLANNING,
        )

        with pytest.raises(HTTPException) as exc_info:
            project_service.update_user_project(
                db=db_session,
                project_id=99999,
                project_in=update_data,
                owner_id=test_user.id,
            )

        assert exc_info.value.status_code == 404
        assert "Proyecto no encontrado" in exc_info.value.detail

    def test_delete_user_project_success(self, db_session, test_user, test_project):
        """Probar eliminación exitosa de proyecto"""
        project_id = test_project.id

        result = project_service.delete_user_project(
            db=db_session, project_id=project_id, owner_id=test_user.id
        )

        assert result is True

        # Verificar que el proyecto fue eliminado
        deleted_project = (
            db_session.query(Project).filter(Project.id == project_id).first()
        )
        assert deleted_project is None

    def test_delete_user_project_not_found(self, db_session, test_user):
        """Probar eliminación de proyecto que no existe"""
        with pytest.raises(HTTPException) as exc_info:
            project_service.delete_user_project(
                db=db_session, project_id=99999, owner_id=test_user.id
            )

        assert exc_info.value.status_code == 404
        assert "Proyecto no encontrado" in exc_info.value.detail

    def test_get_project_with_phases_success(self, db_session, test_user, test_project):
        """Probar obtener proyecto con sus fases"""
        result = project_service.get_project_with_phases(
            db=db_session, project_id=test_project.id, owner_id=test_user.id
        )

        assert result is not None
        assert result.id == test_project.id
        # Verificar que tiene la relación de fases (aunque esté vacía)
        assert hasattr(result, "phases")

    def test_get_project_with_phases_not_found(self, db_session, test_user):
        """Probar obtener fases de proyecto que no existe"""
        with pytest.raises(HTTPException) as exc_info:
            project_service.get_project_with_phases(
                db=db_session, project_id=99999, owner_id=test_user.id
            )

        assert exc_info.value.status_code == 404
        assert "Proyecto no encontrado" in exc_info.value.detail

    def test_search_user_projects_by_name_success(self, db_session, test_user):
        """Probar búsqueda de proyectos por nombre exitosamente"""
        # Crear proyectos con diferentes nombres
        projects_data = [
            {"name": "Machine Learning Project", "description": "ML Desc"},
            {"name": "Deep Learning Research", "description": "DL Desc"},
            {"name": "Data Science Analysis", "description": "DS Desc"},
        ]

        for data in projects_data:
            project = Project(
                name=data["name"],
                description=data["description"],
                owner_id=test_user.id,
                status="planning",
            )
            db_session.add(project)

        db_session.commit()

        # Buscar proyectos que contengan "Learning"
        result = project_service.search_user_projects_by_name(
            db=db_session, query="Learning", owner_id=test_user.id
        )

        assert isinstance(result, list)
        assert len(result) == 2  # Machine Learning y Deep Learning

    def test_search_user_projects_by_name_no_results(self, db_session, test_user):
        """Probar búsqueda de proyectos sin resultados"""
        # Crear un proyecto
        project = Project(
            name="Test Project",
            description="Test Description",
            owner_id=test_user.id,
            status="planning",
        )
        db_session.add(project)
        db_session.commit()

        # Buscar con un término que no existe
        result = project_service.search_user_projects_by_name(
            db=db_session, query="Inexistente", owner_id=test_user.id
        )

        assert isinstance(result, list)
        assert len(result) == 0

    def test_search_user_projects_by_name_case_insensitive(self, db_session, test_user):
        """Probar que la búsqueda sea case-insensitive"""
        # Crear proyecto
        project = Project(
            name="Machine Learning Project",
            description="ML Description",
            owner_id=test_user.id,
            status="planning",
        )
        db_session.add(project)
        db_session.commit()

        # Buscar con diferentes casos
        result_lower = project_service.search_user_projects_by_name(
            db=db_session, query="machine", owner_id=test_user.id
        )
        result_upper = project_service.search_user_projects_by_name(
            db=db_session, query="MACHINE", owner_id=test_user.id
        )
        result_mixed = project_service.search_user_projects_by_name(
            db=db_session, query="MaChInE", owner_id=test_user.id
        )

        assert len(result_lower) == 1
        assert len(result_upper) == 1
        assert len(result_mixed) == 1
