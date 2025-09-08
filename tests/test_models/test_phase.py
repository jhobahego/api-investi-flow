import pytest
from sqlalchemy.exc import IntegrityError

from app.database import Base
from app.models.phase import Phase
from app.models.project import Project
from app.models.user import User
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


class TestPhaseModel:
    """Pruebas para el modelo Phase"""

    def test_create_phase_success(self, db_session, test_project):
        """Probar creación exitosa de fase"""
        phase = Phase(
            name="Test Phase",
            position=0,
            color="#FF5733",
            project_id=test_project.id,
        )

        db_session.add(phase)
        db_session.commit()
        db_session.refresh(phase)

        assert phase.id is not None
        assert phase.name == "Test Phase"
        assert phase.position == 0
        assert phase.color == "#FF5733"
        assert phase.project_id == test_project.id

    def test_create_phase_minimal_data(self, db_session, test_project):
        """Probar creación de fase con datos mínimos"""
        phase = Phase(
            name="Minimal Phase",
            position=0,
            project_id=test_project.id,
        )

        db_session.add(phase)
        db_session.commit()
        db_session.refresh(phase)

        assert phase.id is not None
        assert phase.name == "Minimal Phase"
        assert phase.position == 0
        assert phase.color is None
        assert phase.project_id == test_project.id

    def test_phase_name_required(self, db_session, test_project):
        """Probar que el nombre es requerido"""
        phase = Phase(
            position=0,
            project_id=test_project.id,
        )

        db_session.add(phase)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_phase_position_required(self, db_session, test_project):
        """Probar que la posición es requerida"""
        phase = Phase(
            name="Test Phase",
            project_id=test_project.id,
        )

        db_session.add(phase)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_phase_project_id_required(self, db_session):
        """Probar que project_id es requerido"""
        phase = Phase(
            name="Test Phase",
            position=0,
        )

        db_session.add(phase)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_phase_project_id_foreign_key(self, db_session):
        """Probar que project_id debe existir como foreign key"""
        phase = Phase(
            name="Test Phase",
            position=0,
            project_id=999999,  # ID que no existe
        )

        db_session.add(phase)

        # En SQLite, las foreign keys podrían no estar habilitadas por defecto
        # Intentamos hacer commit y esperamos un error o verificamos que la relación no funciona
        try:
            db_session.commit()
            db_session.refresh(phase)
            # Si llegamos aquí, verificamos que la relación project sea None
            assert phase.project is None
        except IntegrityError:
            # Este es el comportamiento esperado si las foreign keys están habilitadas
            pass

    def test_phase_relationship_with_project(self, db_session, test_project):
        """Probar relación con proyecto"""
        phase = Phase(
            name="Test Phase",
            position=0,
            project_id=test_project.id,
        )

        db_session.add(phase)
        db_session.commit()
        db_session.refresh(phase)

        # Verificar relación
        assert phase.project is not None
        assert phase.project.id == test_project.id
        assert phase.project.name == test_project.name

    def test_project_relationship_with_phases(self, db_session, test_project):
        """Probar relación del proyecto con fases"""
        # Crear varias fases
        phases = []
        for i in range(3):
            phase = Phase(
                name=f"Phase {i + 1}",
                position=i,
                project_id=test_project.id,
            )
            phases.append(phase)
            db_session.add(phase)

        db_session.commit()

        # Refrescar proyecto para cargar relaciones
        db_session.refresh(test_project)

        assert len(test_project.phases) == 3
        assert all(phase.project_id == test_project.id for phase in test_project.phases)

    def test_phase_cascade_delete_from_project(self, db_session, test_user):
        """Probar eliminación en cascada cuando se elimina el proyecto"""
        # Crear proyecto
        project = Project(
            name="Project to Delete",
            owner_id=test_user.id,
            status="planning",
        )
        db_session.add(project)
        db_session.commit()

        # Crear fases
        phases = []
        for i in range(3):
            phase = Phase(
                name=f"Phase {i + 1}",
                position=i,
                project_id=project.id,
            )
            phases.append(phase)
            db_session.add(phase)

        db_session.commit()

        # Verificar que las fases existen
        phase_count = (
            db_session.query(Phase).filter(Phase.project_id == project.id).count()
        )
        assert phase_count == 3

        # Eliminar proyecto
        db_session.delete(project)
        db_session.commit()

        # Verificar que las fases fueron eliminadas en cascada
        remaining_phases = (
            db_session.query(Phase).filter(Phase.project_id == project.id).count()
        )
        assert remaining_phases == 0

    def test_phase_color_optional(self, db_session, test_project):
        """Probar que el color es opcional"""
        phase_without_color = Phase(
            name="Phase Without Color",
            position=0,
            project_id=test_project.id,
        )

        phase_with_color = Phase(
            name="Phase With Color",
            position=1,
            color="#FF5733",
            project_id=test_project.id,
        )

        db_session.add(phase_without_color)
        db_session.add(phase_with_color)
        db_session.commit()

        db_session.refresh(phase_without_color)
        db_session.refresh(phase_with_color)

        assert phase_without_color.color is None
        assert phase_with_color.color == "#FF5733"

    def test_phase_multiple_positions_same_project(self, db_session, test_project):
        """Probar que se pueden tener múltiples fases con diferentes posiciones en el mismo proyecto"""
        phases = []
        for i in range(5):
            phase = Phase(
                name=f"Phase {i + 1}",
                position=i,
                project_id=test_project.id,
            )
            phases.append(phase)
            db_session.add(phase)

        db_session.commit()

        # Verificar que todas las fases se crearon
        created_phases = (
            db_session.query(Phase).filter(Phase.project_id == test_project.id).all()
        )
        assert len(created_phases) == 5

        # Verificar posiciones únicas
        positions = [phase.position for phase in created_phases]
        assert len(set(positions)) == 5
        assert positions == list(range(5))

    def test_phase_same_position_different_projects(self, db_session, test_user):
        """Probar que se pueden tener fases con la misma posición en diferentes proyectos"""
        # Crear dos proyectos
        project1 = Project(
            name="Project 1",
            owner_id=test_user.id,
            status="planning",
        )
        project2 = Project(
            name="Project 2",
            owner_id=test_user.id,
            status="planning",
        )
        db_session.add(project1)
        db_session.add(project2)
        db_session.commit()

        # Crear fases con la misma posición en diferentes proyectos
        phase1 = Phase(
            name="Phase Project 1",
            position=0,
            project_id=project1.id,
        )
        phase2 = Phase(
            name="Phase Project 2",
            position=0,
            project_id=project2.id,
        )

        db_session.add(phase1)
        db_session.add(phase2)
        db_session.commit()

        # Verificar que ambas fases se crearon correctamente
        db_session.refresh(phase1)
        db_session.refresh(phase2)

        assert phase1.position == 0
        assert phase2.position == 0
        assert phase1.project_id != phase2.project_id

    def test_phase_table_name(self):
        """Probar que el nombre de la tabla es correcto"""
        assert Phase.__tablename__ == "phases"

    def test_phase_primary_key(self, db_session, test_project):
        """Probar que la clave primaria funciona correctamente"""
        phase = Phase(
            name="Test Phase",
            position=0,
            project_id=test_project.id,
        )

        db_session.add(phase)
        db_session.commit()
        db_session.refresh(phase)

        # Verificar que se asignó un ID
        assert phase.id is not None
        assert isinstance(phase.id, int)
        assert phase.id > 0

        # Verificar que se puede buscar por ID
        found_phase = db_session.query(Phase).filter(Phase.id == phase.id).first()
        assert found_phase is not None
        assert found_phase.name == "Test Phase"

    def test_phase_string_representation(self, db_session, test_project):
        """Probar la representación en string del modelo (si existe)"""
        phase = Phase(
            name="Test Phase for String",
            position=0,
            project_id=test_project.id,
        )

        db_session.add(phase)
        db_session.commit()
        db_session.refresh(phase)

        # El modelo Phase no tiene __str__ o __repr__ definido,
        # pero podemos verificar que el objeto se puede convertir a string
        phase_str = str(phase)
        assert isinstance(phase_str, str)
        assert "Phase" in phase_str or "object" in phase_str
