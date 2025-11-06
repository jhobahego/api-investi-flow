"""Tests para los schemas de Task"""

from datetime import datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.task import TaskCreate, TaskResponse, TaskStatus, TaskUpdate


class TestTaskSchemas:
    """Pruebas para los schemas de tarea"""

    def test_task_create_minimal_fields(self):
        """Probar creación de TaskCreate con campos mínimos"""
        task_data = {"title": "Test Task", "position": 0, "phase_id": 1}

        task = TaskCreate(**task_data)

        assert task.title == "Test Task"
        assert task.position == 0
        assert task.phase_id == 1
        assert task.status == TaskStatus.PENDING  # Valor por defecto
        assert task.completed is False  # Valor por defecto

    def test_task_create_all_fields(self):
        """Probar creación de TaskCreate con todos los campos"""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=7)

        task_data = {
            "title": "Complete Task",
            "description": "Descripción detallada",
            "position": 1,
            "status": TaskStatus.IN_PROGRESS,
            "completed": False,
            "start_date": start_date,
            "end_date": end_date,
            "phase_id": 1,
        }

        task = TaskCreate(**task_data)

        assert task.title == "Complete Task"
        assert task.description == "Descripción detallada"
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.start_date == start_date
        assert task.end_date == end_date

    def test_task_create_empty_title(self):
        """Probar validación con título vacío"""
        task_data = {"title": "", "position": 0, "phase_id": 1}

        with pytest.raises(ValidationError):
            TaskCreate(**task_data)

    def test_task_create_invalid_status(self):
        """Probar validación con status inválido"""
        task_data = {
            "title": "Test Task",
            "position": 0,
            "phase_id": 1,
            "status": "invalid_status",
        }

        with pytest.raises(ValidationError):
            TaskCreate(**task_data)

    def test_task_create_valid_statuses(self):
        """Probar todos los statuses válidos"""
        valid_statuses = [
            TaskStatus.PENDING,
            TaskStatus.IN_PROGRESS,
            TaskStatus.COMPLETED,
        ]

        for status in valid_statuses:
            task_data = {
                "title": "Test Task",
                "position": 0,
                "phase_id": 1,
                "status": status,
            }
            task = TaskCreate(**task_data)
            assert task.status == status

    def test_task_create_negative_position(self):
        """Probar validación con posición negativa"""
        task_data = {"title": "Test Task", "position": -1, "phase_id": 1}

        with pytest.raises(ValidationError):
            TaskCreate(**task_data)

    def test_task_update_partial_fields(self):
        """Probar actualización parcial de tarea"""
        update_data: dict[str, Any] = {"title": "Updated Title"}

        task_update = TaskUpdate(**update_data)  # type: ignore[arg-type]

        assert task_update.title == "Updated Title"
        assert task_update.description is None
        assert task_update.status is None

    def test_task_update_all_fields(self):
        """Probar actualización con todos los campos"""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=7)

        update_data = {
            "title": "Updated Task",
            "description": "Updated Description",
            "position": 2,
            "status": TaskStatus.COMPLETED,
            "completed": True,
            "start_date": start_date,
            "end_date": end_date,
        }

        task_update = TaskUpdate(**update_data)

        assert task_update.title == "Updated Task"
        assert task_update.description == "Updated Description"
        assert task_update.status == TaskStatus.COMPLETED
        assert task_update.completed is True

    def test_task_update_empty_title(self):
        """Probar validación con título vacío en actualización"""
        update_data: dict[str, Any] = {"title": ""}

        with pytest.raises(ValidationError):
            TaskUpdate(**update_data)  # type: ignore[arg-type]

    def test_task_response_from_dict(self):
        """Probar creación de TaskResponse desde diccionario"""
        from datetime import datetime

        task_data = {
            "id": 1,
            "title": "Response Task",
            "description": "Description",
            "position": 0,
            "status": TaskStatus.PENDING,
            "completed": False,
            "phase_id": 1,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        task_response = TaskResponse(**task_data)

        assert task_response.id == 1
        assert task_response.title == "Response Task"
        assert task_response.description == "Description"
        assert task_response.status == TaskStatus.PENDING
        assert task_response.completed is False

    def test_task_response_optional_fields(self):
        """Probar TaskResponse con campos opcionales"""
        from datetime import datetime

        task_data = {
            "id": 1,
            "title": "Test Task",
            "description": None,
            "position": 0,
            "status": TaskStatus.PENDING,
            "completed": False,
            "start_date": None,
            "end_date": None,
            "phase_id": 1,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        task_response = TaskResponse(**task_data)

        assert task_response.description is None
        assert task_response.start_date is None
        assert task_response.end_date is None

    def test_task_status_enum_values(self):
        """Probar valores del enum TaskStatus"""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.IN_PROGRESS == "in_progress"
        assert TaskStatus.COMPLETED == "completed"

    def test_task_response_with_dates(self):
        """Probar TaskResponse con fechas"""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=7)
        created_at = datetime.now()

        task_data = {
            "id": 1,
            "title": "Task With Dates",
            "position": 0,
            "status": TaskStatus.IN_PROGRESS,
            "completed": False,
            "start_date": start_date,
            "end_date": end_date,
            "phase_id": 1,
            "created_at": created_at,
            "updated_at": created_at,
        }

        task_response = TaskResponse(**task_data)

        assert task_response.start_date == start_date
        assert task_response.end_date == end_date
        assert (
            task_response.end_date is not None
            and task_response.start_date is not None
            and task_response.end_date > task_response.start_date
        )
