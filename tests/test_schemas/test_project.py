"""Tests para los schemas de Project"""

import pytest
from pydantic import ValidationError

from app.models.project import ResearchType
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate


class TestProjectSchemas:
    """Pruebas para los schemas de proyecto"""

    def test_project_create_minimal_fields(self):
        """Probar creación de ProjectCreate con campos mínimos"""
        project_data = {
            "name": "Test Project",
            "research_type": None,
        }

        project = ProjectCreate(**project_data)

        assert project.name == "Test Project"
        assert project.description is None
        assert project.status == "planning"  # Valor por defecto

    def test_project_create_all_fields(self):
        """Probar creación de ProjectCreate con todos los campos"""
        project_data = {
            "name": "Complete Project",
            "description": "Descripción detallada",
            "research_type": ResearchType.EXPERIMENTAL,
            "institution": "Universidad Test",
            "research_group": "Grupo Test",
            "category": "Tecnología",
            "status": "in_progress",
        }

        project = ProjectCreate(**project_data)

        assert project.name == "Complete Project"
        assert project.description == "Descripción detallada"
        assert project.research_type == "experimental"
        assert project.institution == "Universidad Test"
        assert project.status == "in_progress"

    def test_project_create_empty_name(self):
        """Probar validación con nombre vacío"""
        project_data = {"name": "", "research_type": None}

        with pytest.raises(ValidationError):
            ProjectCreate(**project_data)

    def test_project_create_invalid_status(self):
        """Probar validación con status inválido"""
        project_data = {
            "name": "Test Project",
            "research_type": None,
            "status": "invalid_status",
        }

        with pytest.raises(ValidationError) as exc_info:
            ProjectCreate(**project_data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("status",) for error in errors)

    def test_project_create_valid_statuses(self):
        """Probar todos los statuses válidos"""
        from app.models.project import ProjectStatus

        valid_statuses = [
            ProjectStatus.PLANNING,
            ProjectStatus.IN_PROGRESS,
            ProjectStatus.COMPLETED,
            ProjectStatus.ON_HOLD,
        ]

        for status in valid_statuses:
            project_data = {"name": "Test Project", "status": status}
            project = ProjectCreate(**project_data)
            assert project.status == status

    def test_project_update_partial_fields(self):
        """Probar actualización parcial de proyecto"""
        update_data = {"name": "Updated Name", "research_type": None}

        project_update = ProjectUpdate(**update_data)

        assert project_update.name == "Updated Name"
        assert project_update.description is None
        assert project_update.status is None

    def test_project_update_all_fields(self):
        """Probar actualización con todos los campos"""
        update_data = {
            "name": "Updated Project",
            "description": "Updated Description",
            "institution": "New Institution",
            "research_group": "New Group",
            "research_type": ResearchType.THEORETICAL,
            "category": "Science",
            "status": "completed",
        }

        project_update = ProjectUpdate(**update_data)

        assert project_update.name == "Updated Project"
        assert project_update.description == "Updated Description"
        assert project_update.status == "completed"

    def test_project_update_empty_name(self):
        """Probar validación con nombre vacío en actualización"""
        update_data = {"name": "", "research_type": None}

        with pytest.raises(ValidationError):
            ProjectUpdate(**update_data)

    def test_project_response_from_dict(self):
        """Probar creación de ProjectResponse desde diccionario"""
        from datetime import datetime

        from app.models.project import ProjectStatus

        project_data = {
            "id": 1,
            "name": "Response Project",
            "description": "Description",
            "status": ProjectStatus.PLANNING,
            "owner_id": 1,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        project_response = ProjectResponse(**project_data)

        assert project_response.id == 1
        assert project_response.name == "Response Project"
        assert project_response.description == "Description"
        assert project_response.status == ProjectStatus.PLANNING
        assert project_response.owner_id == 1

    def test_project_response_optional_fields(self):
        """Probar ProjectResponse con campos opcionales"""
        from datetime import datetime

        from app.models.project import ProjectStatus

        project_data = {
            "id": 1,
            "name": "Test Project",
            "description": None,
            "research_type": None,
            "institution": None,
            "research_group": None,
            "category": None,
            "status": ProjectStatus.PLANNING,
            "owner_id": 1,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        project_response = ProjectResponse(**project_data)

        assert project_response.description is None
        assert project_response.research_type is None
        assert project_response.institution is None

    def test_project_response_with_relationships(self):
        """Probar ProjectResponse puede incluir relaciones"""
        from datetime import datetime

        from app.models.project import ProjectStatus

        # Nota: Esto depende de la configuración de from_attributes en el schema
        project_data = {
            "id": 1,
            "name": "Test Project",
            "status": ProjectStatus.PLANNING,
            "owner_id": 1,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        project_response = ProjectResponse(**project_data)

        assert project_response.id == 1
        assert project_response.name == "Test Project"
