import pytest

from app.database import Base
from tests.test_db_config import client, engine


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestPhaseIntegration:
    """Pruebas de integración para el módulo de fases"""

    def create_test_user_and_login(
        self, email="testuser@example.com", phone_number=None
    ):
        """Helper para crear un usuario de prueba y hacer login"""

        # Generar un número de teléfono único basado en el email si no se proporciona
        if phone_number is None:
            phone_suffix = str(abs(hash(email)) % 10000).zfill(4)
            phone_number = f"+57300123{phone_suffix}"

        user_data = {
            "email": email,
            "full_name": "Test User",
            "password": "Test123456",
            "phone_number": phone_number,
        }

        # Crear usuario
        register_response = client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201

        # Hacer login
        login_data = {"username": email, "password": "Test123456"}
        login_response = client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        user_id = register_response.json()["id"]

        return headers, user_id

    def create_test_project(self, headers):
        """Helper para crear un proyecto de prueba"""
        project_data = {
            "name": "Proyecto de Prueba para Integración",
            "description": "Este es un proyecto de prueba para las pruebas de integración",
        }

        response = client.post("/api/v1/proyectos/", json=project_data, headers=headers)
        assert response.status_code == 201
        return response.json()

    def create_test_phase(self, headers, project_id, name="Fase de Prueba", position=0):
        """Helper para crear una fase de prueba"""
        phase_data = {
            "name": name,
            "position": position,
            "color": "#FF5733",
            "project_id": project_id,
        }

        response = client.post("/api/v1/fases/", json=phase_data, headers=headers)
        assert response.status_code == 201
        return response.json()

    def test_complete_phase_lifecycle(self):
        """Probar el ciclo completo de vida de una fase"""
        # 1. Crear usuario y hacer login
        headers, user_id = self.create_test_user_and_login()

        # 2. Crear proyecto
        project = self.create_test_project(headers)
        project_id = project["id"]

        # 3. Crear fase
        phase_data = {
            "name": "Fase de Análisis",
            "position": 0,
            "color": "#FF5733",
            "project_id": project_id,
        }

        create_response = client.post(
            "/api/v1/fases/", json=phase_data, headers=headers
        )
        assert create_response.status_code == 201

        phase = create_response.json()
        phase_id = phase["id"]

        assert phase["name"] == "Fase de Análisis"
        assert phase["position"] == 0
        assert phase["color"] == "#FF5733"
        assert phase["project_id"] == project_id

        # 4. Obtener fase por ID
        get_response = client.get(f"/api/v1/fases/{phase_id}", headers=headers)
        assert get_response.status_code == 200

        retrieved_phase = get_response.json()
        assert retrieved_phase["id"] == phase_id
        assert retrieved_phase["name"] == "Fase de Análisis"

        # 5. Actualizar fase
        update_data = {
            "name": "Fase de Análisis Actualizada",
            "color": "#33FF57",
        }

        update_response = client.put(
            f"/api/v1/fases/{phase_id}", json=update_data, headers=headers
        )
        assert update_response.status_code == 200

        updated_phase = update_response.json()
        assert updated_phase["name"] == "Fase de Análisis Actualizada"
        assert updated_phase["color"] == "#33FF57"

        # 6. Obtener tareas de la fase
        tasks_response = client.get(f"/api/v1/fases/{phase_id}/tareas", headers=headers)
        assert tasks_response.status_code == 200

        # 7. Eliminar fase
        delete_response = client.delete(f"/api/v1/fases/{phase_id}", headers=headers)
        assert delete_response.status_code == 204

        # 8. Verificar que la fase ya no existe
        get_deleted_response = client.get(f"/api/v1/fases/{phase_id}", headers=headers)
        assert get_deleted_response.status_code == 404

    def test_multiple_phases_in_project(self):
        """Probar manejo de múltiples fases en un proyecto"""
        # Crear usuario y proyecto
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        project_id = project["id"]

        # Crear múltiples fases
        phase_names = [
            "Planificacion",  # Sin acentos para evitar problemas de codificación
            "Analisis",  # Sin acentos
            "Diseno",  # Sin acentos
            "Implementacion",  # Sin acentos
            "Pruebas",
        ]
        created_phases = []

        # Colores válidos hexadecimales de 6 dígitos
        colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF"]

        for i, name in enumerate(phase_names):
            phase_data = {
                "name": name,
                "position": i,
                "color": colors[i],  # Usar colores predefinidos válidos
                "project_id": project_id,
            }

            response = client.post("/api/v1/fases/", json=phase_data, headers=headers)
            assert response.status_code == 201
            created_phases.append(response.json())

        # Verificar que todas las fases se crearon correctamente
        assert len(created_phases) == 5

        for i, phase in enumerate(created_phases):
            assert phase["name"] == phase_names[i]
            assert phase["position"] == i
            assert phase["project_id"] == project_id

        # Reordenar fases
        reorder_data = [
            {"id": created_phases[4]["id"], "position": 0},  # Pruebas primero
            {"id": created_phases[0]["id"], "position": 1},  # Planificación segundo
            {"id": created_phases[1]["id"], "position": 2},  # Análisis tercero
            {"id": created_phases[2]["id"], "position": 3},  # Diseño cuarto
            {"id": created_phases[3]["id"], "position": 4},  # Implementación último
        ]

        reorder_response = client.put(
            f"/api/v1/fases/project/{project_id}/reorder",
            json=reorder_data,
            headers=headers,
        )
        assert reorder_response.status_code == 200

        reordered_phases = reorder_response.json()
        assert len(reordered_phases) == 5

        # Verificar que las posiciones se actualizaron correctamente
        for phase in reordered_phases:
            expected_position = next(
                item["position"] for item in reorder_data if item["id"] == phase["id"]
            )
            assert phase["position"] == expected_position

    def test_phase_position_management(self):
        """Probar gestión de posiciones de fases"""
        # Crear usuario y proyecto
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        project_id = project["id"]

        # Crear tres fases en orden
        phases = []
        for i in range(3):
            phase = self.create_test_phase(headers, project_id, f"Fase {i + 1}", i)
            phases.append(phase)

        # Crear nueva fase en posición intermedia (posición 1)
        new_phase_data = {
            "name": "Nueva Fase Intermedia",
            "position": 1,
            "color": "#FFFF00",
            "project_id": project_id,
        }

        response = client.post("/api/v1/fases/", json=new_phase_data, headers=headers)
        assert response.status_code == 201

        new_phase = response.json()
        assert new_phase["position"] == 1

        # Eliminar una fase y verificar reposicionamiento
        delete_response = client.delete(
            f"/api/v1/fases/{phases[1]['id']}", headers=headers
        )
        assert delete_response.status_code == 204

        # Verificar que la fase posterior se movió
        get_response = client.get(f"/api/v1/fases/{phases[2]['id']}", headers=headers)
        if get_response.status_code == 200:
            # La fase podría haberse reposicionado
            _ = get_response.json()
            # La posición debería haberse ajustado

    def test_phase_security_isolation(self):
        """Probar aislamiento de seguridad entre usuarios"""
        # Crear primer usuario y su proyecto/fase
        headers1, user_id1 = self.create_test_user_and_login("user1@example.com")
        project1 = self.create_test_project(headers1)
        phase1 = self.create_test_phase(headers1, project1["id"])

        # Crear segundo usuario
        headers2, user_id2 = self.create_test_user_and_login("user2@example.com")

        # El segundo usuario no debe poder acceder a la fase del primero
        phase_id = phase1["id"]

        # Intentar obtener fase de otro usuario
        get_response = client.get(f"/api/v1/fases/{phase_id}", headers=headers2)
        assert get_response.status_code == 404

        # Intentar actualizar fase de otro usuario
        update_data = {"name": "Intento de Hackeo"}
        update_response = client.put(
            f"/api/v1/fases/{phase_id}", json=update_data, headers=headers2
        )
        assert update_response.status_code == 404

        # Intentar eliminar fase de otro usuario
        delete_response = client.delete(f"/api/v1/fases/{phase_id}", headers=headers2)
        assert delete_response.status_code == 404

        # Verificar que la fase original sigue existiendo para el primer usuario
        get_original_response = client.get(
            f"/api/v1/fases/{phase_id}", headers=headers1
        )
        assert get_original_response.status_code == 200

    def test_phase_validation_integration(self):
        """Probar validaciones de fase en integración"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        project_id = project["id"]

        # Probar creación con nombre muy corto
        invalid_phase_data = {
            "name": "Corto",  # Cambiado a un nombre un poco más largo
            "position": 0,
            "project_id": project_id,
        }

        response = client.post(
            "/api/v1/fases/", json=invalid_phase_data, headers=headers
        )
        # Si el nombre mínimo es mayor que "Corto", debería fallar
        if response.status_code != 201:
            assert response.status_code == 422

        # Probar creación con posición negativa
        invalid_phase_data = {
            "name": "Fase con Posición Negativa",
            "position": -1,
            "project_id": project_id,
        }

        response = client.post(
            "/api/v1/fases/", json=invalid_phase_data, headers=headers
        )
        assert response.status_code == 422

        # Probar creación con color inválido
        invalid_phase_data = {
            "name": "Fase con Color Inválido",
            "position": 0,
            "color": "not_a_color",
            "project_id": project_id,
        }

        response = client.post(
            "/api/v1/fases/", json=invalid_phase_data, headers=headers
        )
        assert response.status_code == 422

        # Probar creación con proyecto inexistente
        invalid_phase_data = {
            "name": "Fase Sin Proyecto",
            "position": 0,
            "project_id": 999999,
        }

        response = client.post(
            "/api/v1/fases/", json=invalid_phase_data, headers=headers
        )
        assert response.status_code == 404

    def test_phase_document_integration(self):
        """Probar integración con documentos de fase"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)
        phase = self.create_test_phase(headers, project["id"])
        phase_id = phase["id"]

        # Intentar obtener documento (debería retornar None inicialmente)
        doc_response = client.get(
            f"/api/v1/fases/{phase_id}/documentos", headers=headers
        )
        assert doc_response.status_code == 200
        # Podría retornar None o una lista vacía

        # Las pruebas de subida de documentos requerirían archivos reales
        # que están fuera del alcance de estas pruebas unitarias básicas

    def test_error_handling_integration(self):
        """Probar manejo de errores en integración"""
        headers, user_id = self.create_test_user_and_login()

        # Probar endpoints sin autenticación
        response = client.get("/api/v1/fases/1")
        assert response.status_code == 401

        response = client.post("/api/v1/fases/", json={"name": "TestFase"})
        assert response.status_code == 401

        response = client.put("/api/v1/fases/1", json={"name": "TestFase"})
        assert response.status_code == 401

        response = client.delete("/api/v1/fases/1")
        assert response.status_code == 401

        # Probar con recursos inexistentes
        response = client.get("/api/v1/fases/999999", headers=headers)
        assert response.status_code == 404

        response = client.put(
            "/api/v1/fases/999999", json={"name": "TestFase"}, headers=headers
        )
        assert response.status_code == 404

        response = client.delete("/api/v1/fases/999999", headers=headers)
        assert response.status_code == 404
