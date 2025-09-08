from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.phase import (
    PhaseBase,
    PhaseCreate,
    PhaseDetailResponse,
    PhaseListResponse,
    PhaseOrder,
    PhaseResponse,
    PhaseUpdate,
    PhaseWithTasksResponse,
)


class TestPhaseSchemas:
    """Pruebas para los esquemas Pydantic de Phase"""

    def test_phase_base_valid_data(self):
        """Probar PhaseBase con datos válidos"""
        phase_data = {
            "name": "Fase de Análisis",
            "position": 0,
            "color": "#FF5733",
        }

        phase = PhaseBase(**phase_data)

        assert phase.name == "Fase de Análisis"
        assert phase.position == 0
        assert phase.color == "#FF5733"

    def test_phase_base_minimal_data(self):
        """Probar PhaseBase con datos mínimos"""
        phase_data = {
            "name": "Fase Mínima",
            "position": 0,
        }

        phase = PhaseBase(**phase_data)

        assert phase.name == "Fase Mínima"
        assert phase.position == 0
        assert phase.color is None

    def test_phase_base_name_validation(self):
        """Probar validación del nombre en PhaseBase"""
        # Nombre muy corto
        with pytest.raises(ValidationError) as exc_info:
            PhaseBase(name="ABC", position=0)

        error_messages = str(exc_info.value)
        assert "at least 5 characters" in error_messages

        # Nombre vacío
        with pytest.raises(ValidationError) as exc_info:
            PhaseBase(name="", position=0)

        error_messages = str(exc_info.value)
        assert "at least 5 characters" in error_messages

        # Nombre solo espacios
        with pytest.raises(ValidationError) as exc_info:
            PhaseBase(name="   ", position=0)

        error_messages = str(exc_info.value)
        assert "at least 5 characters" in error_messages

    def test_phase_base_name_trimming(self):
        """Probar que el nombre se recorta automáticamente"""
        phase = PhaseBase(name="   Fase con Espacios   ", position=0)
        assert phase.name == "Fase con Espacios"

    def test_phase_base_position_validation(self):
        """Probar validación de posición en PhaseBase"""
        # Posición negativa
        with pytest.raises(ValidationError) as exc_info:
            PhaseBase(name="Fase Válida", position=-1)

        error_messages = str(exc_info.value)
        assert "greater than or equal to 0" in error_messages

        # Posición válida en 0
        phase = PhaseBase(name="Fase Válida", position=0)
        assert phase.position == 0

        # Posición válida positiva
        phase = PhaseBase(name="Fase Válida", position=5)
        assert phase.position == 5

    def test_phase_base_color_validation(self):
        """Probar validación de color en PhaseBase"""
        # Color válido
        phase = PhaseBase(name="Fase Válida", position=0, color="#FF5733")
        assert phase.color == "#FF5733"

        # Color sin #
        with pytest.raises(ValidationError) as exc_info:
            PhaseBase(name="Fase Válida", position=0, color="FF5733")

        error_messages = str(exc_info.value)
        assert "formato hexadecimal" in error_messages

        # Color muy corto
        with pytest.raises(ValidationError) as exc_info:
            PhaseBase(name="Fase Válida", position=0, color="#FF")

        error_messages = str(exc_info.value)
        assert "formato hexadecimal" in error_messages

        # Color muy largo
        with pytest.raises(ValidationError) as exc_info:
            PhaseBase(name="Fase Válida", position=0, color="#FF5733AA")

        error_messages = str(exc_info.value)
        assert "at most 7 characters" in error_messages

        # Color con caracteres inválidos
        with pytest.raises(ValidationError) as exc_info:
            PhaseBase(name="Fase Válida", position=0, color="#GG5733")

        error_messages = str(exc_info.value)
        assert "valor hexadecimal válido" in error_messages

    def test_phase_base_color_none(self):
        """Probar que color puede ser None"""
        phase = PhaseBase(name="Fase Sin Color", position=0, color=None)
        assert phase.color is None

    def test_phase_create_valid_data(self):
        """Probar PhaseCreate con datos válidos"""
        phase_data = {
            "name": "Nueva Fase",
            "position": 1,
            "color": "#33FF57",
            "project_id": 123,
        }

        phase = PhaseCreate(**phase_data)

        assert phase.name == "Nueva Fase"
        assert phase.position == 1
        assert phase.color == "#33FF57"
        assert phase.project_id == 123

    def test_phase_create_missing_project_id(self):
        """Probar PhaseCreate sin project_id requerido"""
        with pytest.raises(ValidationError) as exc_info:
            PhaseCreate(name="Fase Sin Proyecto", position=0)

        error_messages = str(exc_info.value)
        assert "required" in error_messages.lower()

    def test_phase_update_all_fields(self):
        """Probar PhaseUpdate con todos los campos"""
        update_data = {
            "name": "Fase Actualizada",
            "position": 2,
            "color": "#5733FF",
        }

        phase_update = PhaseUpdate(**update_data)

        assert phase_update.name == "Fase Actualizada"
        assert phase_update.position == 2
        assert phase_update.color == "#5733FF"

    def test_phase_update_partial_fields(self):
        """Probar PhaseUpdate con campos parciales"""
        # Solo nombre
        phase_update = PhaseUpdate(name="Solo Nombre")
        assert phase_update.name == "Solo Nombre"
        assert phase_update.position is None
        assert phase_update.color is None

        # Solo posición
        phase_update = PhaseUpdate(position=3)
        assert phase_update.name is None
        assert phase_update.position == 3
        assert phase_update.color is None

        # Solo color
        phase_update = PhaseUpdate(color="#FF3357")
        assert phase_update.name is None
        assert phase_update.position is None
        assert phase_update.color == "#FF3357"

    def test_phase_update_empty(self):
        """Probar PhaseUpdate sin ningún campo"""
        phase_update = PhaseUpdate()
        assert phase_update.name is None
        assert phase_update.position is None
        assert phase_update.color is None

    def test_phase_update_name_validation(self):
        """Probar validación de nombre en PhaseUpdate"""
        # Nombre inválido muy corto
        with pytest.raises(ValidationError) as exc_info:
            PhaseUpdate(name="ABC")

        error_messages = str(exc_info.value)
        assert "at least 5 characters" in error_messages

        # Nombre válido
        phase_update = PhaseUpdate(name="Nombre Válido")
        assert phase_update.name == "Nombre Válido"

    def test_phase_order_valid_data(self):
        """Probar PhaseOrder con datos válidos"""
        order_data = {"id": 123, "position": 2}
        phase_order = PhaseOrder(**order_data)

        assert phase_order.id == 123
        assert phase_order.position == 2

    def test_phase_order_missing_fields(self):
        """Probar PhaseOrder con campos faltantes"""
        # Sin ID
        with pytest.raises(ValidationError):
            PhaseOrder(position=1)

        # Sin posición
        with pytest.raises(ValidationError):
            PhaseOrder(id=123)

    def test_phase_response_with_datetime(self):
        """Probar PhaseResponse con datetime"""
        response_data = {
            "name": "Fase de Respuesta",
            "position": 0,
            "color": "#FF5733",
            "id": 456,
            "created_at": datetime.now(),
        }

        phase_response = PhaseResponse(**response_data)

        assert phase_response.id == 456
        assert phase_response.name == "Fase de Respuesta"
        assert phase_response.position == 0
        assert phase_response.color == "#FF5733"
        assert isinstance(phase_response.created_at, datetime)

    def test_phase_list_response_minimal(self):
        """Probar PhaseListResponse con datos mínimos"""
        list_data = {
            "id": 789,
            "name": "Fase Lista",
            "position": 1,
            "color": None,
            "project_id": 123,
        }

        phase_list = PhaseListResponse(**list_data)

        assert phase_list.id == 789
        assert phase_list.name == "Fase Lista"
        assert phase_list.position == 1
        assert phase_list.color is None
        assert phase_list.project_id == 123

    def test_phase_with_tasks_response_empty_tasks(self):
        """Probar PhaseWithTasksResponse sin tareas"""
        response_data = {
            "name": "Fase Sin Tareas",
            "position": 0,
            "color": "#FF5733",
            "id": 101,
            "created_at": datetime.now(),
            "tasks": [],
        }

        phase_response = PhaseWithTasksResponse(**response_data)

        assert phase_response.id == 101
        assert phase_response.tasks == []

    def test_phase_with_tasks_response_default_tasks(self):
        """Probar PhaseWithTasksResponse con lista de tareas por defecto"""
        response_data = {
            "name": "Fase Con Tareas",
            "position": 0,
            "color": "#FF5733",
            "id": 102,
            "created_at": datetime.now(),
        }

        phase_response = PhaseWithTasksResponse(**response_data)

        assert phase_response.id == 102
        assert phase_response.tasks == []  # Lista vacía por defecto

    def test_phase_detail_response_complete(self):
        """Probar PhaseDetailResponse con todos los campos"""
        response_data = {
            "name": "Fase Detallada",
            "position": 0,
            "color": "#FF5733",
            "id": 103,
            "created_at": datetime.now(),
            "tasks": [],
            "attachment": None,
        }

        phase_detail = PhaseDetailResponse(**response_data)

        assert phase_detail.id == 103
        assert phase_detail.name == "Fase Detallada"
        assert phase_detail.tasks == []
        assert phase_detail.attachment is None

    def test_phase_detail_response_minimal(self):
        """Probar PhaseDetailResponse con datos mínimos"""
        response_data = {
            "name": "Fase Detallada Mínima",
            "position": 0,
            "color": "#FF5733",
            "id": 104,
            "created_at": datetime.now(),
        }

        phase_detail = PhaseDetailResponse(**response_data)

        assert phase_detail.id == 104
        assert phase_detail.tasks == []  # Lista vacía por defecto
        assert phase_detail.attachment is None

    def test_schema_inheritance(self):
        """Probar que las herencias de esquemas funcionan correctamente"""
        # PhaseCreate hereda de PhaseBase
        phase_create = PhaseCreate(
            name="Fase Heredada", position=0, color="#FF5733", project_id=123
        )

        # Debe tener todos los atributos de PhaseBase
        assert hasattr(phase_create, "name")
        assert hasattr(phase_create, "position")
        assert hasattr(phase_create, "color")
        # Más el atributo adicional
        assert hasattr(phase_create, "project_id")

        # PhaseResponse hereda de PhaseBase
        phase_response = PhaseResponse(
            name="Fase Respuesta",
            position=0,
            color="#FF5733",
            id=123,
            created_at=datetime.now(),
        )

        # Debe tener todos los atributos de PhaseBase
        assert hasattr(phase_response, "name")
        assert hasattr(phase_response, "position")
        assert hasattr(phase_response, "color")
        # Más los atributos adicionales
        assert hasattr(phase_response, "id")
        assert hasattr(phase_response, "created_at")

    def test_field_descriptions(self):
        """Probar que los campos tienen las descripciones correctas"""
        # Verificar que los esquemas tienen Field con descripciones
        phase_base_fields = PhaseBase.model_fields

        assert "name" in phase_base_fields
        assert phase_base_fields["name"].description == "Nombre de la fase"

        assert "position" in phase_base_fields
        assert (
            phase_base_fields["position"].description
            == "Posición de la fase en el proyecto"
        )

        assert "color" in phase_base_fields
        assert (
            phase_base_fields["color"].description
            == "Color de la fase en formato hexadecimal"
        )

    def test_model_config_from_attributes(self):
        """Probar que los modelos de respuesta tienen from_attributes configurado"""
        # Verificar que los esquemas de respuesta pueden crear desde atributos
        assert PhaseResponse.model_config.get("from_attributes") is True
        assert PhaseListResponse.model_config.get("from_attributes") is True
        assert PhaseWithTasksResponse.model_config.get("from_attributes") is True
        assert PhaseDetailResponse.model_config.get("from_attributes") is True

    def test_schema_json_serialization(self):
        """Probar serialización JSON de los esquemas"""
        phase_data = {
            "name": "Fase Serializable",
            "position": 0,
            "color": "#FF5733",
            "project_id": 123,
        }

        phase_create = PhaseCreate(**phase_data)

        # Debe poder serializar a JSON
        json_data = phase_create.model_dump()
        assert isinstance(json_data, dict)
        assert json_data["name"] == "Fase Serializable"
        assert json_data["position"] == 0
        assert json_data["color"] == "#FF5733"
        assert json_data["project_id"] == 123

    def test_schema_validation_chain(self):
        """Probar que las validaciones se ejecutan en orden"""
        # El validador de nombre debe ejecutarse y recortar espacios
        phase = PhaseBase(name="   Fase Válida   ", position=0)
        assert phase.name == "Fase Válida"

        # El validador de color debe validar formato
        with pytest.raises(ValidationError) as exc_info:
            PhaseBase(name="Fase Válida", position=0, color="invalid")

        assert "formato hexadecimal" in str(exc_info.value)
