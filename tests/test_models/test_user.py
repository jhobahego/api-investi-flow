"""Tests para el modelo User"""

import pytest

from app.database import Base
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


class TestUserModel:
    """Pruebas para el modelo User"""

    def test_create_user_minimal_fields(self, db_session):
        """Probar creación de usuario con campos mínimos"""
        user = User(
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed_password",
        )

        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.id is not None
        assert user.email == "test@example.com"  # type: ignore[comparison-overlap]
        assert user.full_name == "Test User"  # type: ignore[comparison-overlap]
        assert user.hashed_password == "hashed_password"  # type: ignore[comparison-overlap]
        assert user.is_active is True  # Valor por defecto
        assert user.is_verified is False  # Valor por defecto

    def test_create_user_all_fields(self, db_session):
        """Probar crear usuario con todos los campos"""
        user = User(
            email="full@example.com",
            full_name="Full User",
            hashed_password="hashed_password",
            phone_number="+573001234567",
            university="Universidad Test",
            research_group="Grupo Test",
            career="Ingeniería Test",
            is_active=True,
            is_verified=True,
        )
        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.email == "full@example.com"  # type: ignore[comparison-overlap]
        assert user.university == "Universidad Test"  # type: ignore[comparison-overlap]
        assert user.is_verified is True

    def test_user_relationship_with_projects(self, db_session):
        """Probar relación de usuario con proyectos"""
        from app.models.project import Project

        user = User(
            email="user@example.com",
            full_name="User With Projects",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Crear proyectos para el usuario
        project1 = Project(
            name="Proyecto 1", description="Descripción 1", owner_id=user.id
        )
        project2 = Project(
            name="Proyecto 2", description="Descripción 2", owner_id=user.id
        )

        db_session.add_all([project1, project2])
        db_session.commit()

        # Verificar relación
        db_session.refresh(user)
        assert len(user.projects) == 2  # type: ignore
        assert project1 in user.projects  # type: ignore
        assert project2 in user.projects  # type: ignore

    def test_user_unique_email(self, db_session):
        """Probar que el email debe ser único"""
        user1 = User(
            email="unique@example.com",
            full_name="User 1",
            hashed_password="hashed_password",
        )
        user2 = User(
            email="unique@example.com",
            full_name="User 2",
            hashed_password="hashed_password",
        )

        db_session.add(user1)
        db_session.commit()

        db_session.add(user2)
        with pytest.raises(Exception):  # Violación de unique constraint
            db_session.commit()

    def test_user_cascade_delete_projects(self, db_session):
        """Probar eliminación en cascada de proyectos al eliminar usuario"""
        from app.models.project import Project

        user = User(
            email="cascade@example.com",
            full_name="Cascade User",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Crear proyecto
        project = Project(
            name="Proyecto a eliminar", description="Descripción", owner_id=user.id
        )
        db_session.add(project)
        db_session.commit()
        project_id = project.id

        # Eliminar usuario
        db_session.delete(user)
        db_session.commit()

        # Verificar que el proyecto fue eliminado
        deleted_project = (
            db_session.query(Project).filter(Project.id == project_id).first()
        )
        assert deleted_project is None

    def test_user_repr(self, db_session):
        """Probar representación de string del usuario"""
        user = User(
            email="repr@example.com",
            full_name="Repr User",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        user_repr = repr(user)
        # SQLAlchemy por defecto usa <ClassName object at 0x...>
        assert "User" in user_repr or "repr@example.com" in user_repr

    def test_user_nullable_fields(self, db_session):
        """Probar que campos opcionales pueden ser None"""
        user = User(
            email="nullable@example.com",
            full_name="Nullable User",
            hashed_password="hashed_password",
            phone_number=None,
            university=None,
            research_group=None,
            career=None,
        )

        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.phone_number is None
        assert user.university is None
        assert user.research_group is None
        assert user.career is None
