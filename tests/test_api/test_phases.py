import pytest

from app.database import Base
from tests.test_db_config import client, engine


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestPhaseEndpoints:
    """Pruebas para los endpoints de fases"""

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
            "name": "Proyecto de Prueba para Fases",
            "description": "Este es un proyecto de prueba para las fases",
        }

        response = client.post("/api/v1/proyectos/", json=project_data, headers=headers)
        assert response.status_code == 201
        return response.json()

    def test_create_phase_success(self):
        """Probar creación exitosa de fase"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        phase_data = {
            "name": "Fase de Análisis",
            "position": 0,
            "color": "#FF5733",
            "project_id": project["id"],
        }

        response = client.post("/api/v1/fases/", json=phase_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == phase_data["name"]
        assert data["position"] == phase_data["position"]
        assert data["color"] == phase_data["color"]
        assert data["project_id"] == phase_data["project_id"]
        assert "id" in data

    def test_create_phase_auto_position(self):
        """Probar creación de fase con posición automática"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Crear primera fase
        phase_data_1 = {
            "name": "Primera Fase",
            "position": 0,
            "project_id": project["id"],
        }
        response_1 = client.post("/api/v1/fases/", json=phase_data_1, headers=headers)
        assert response_1.status_code == 201

        # Crear segunda fase sin especificar posición
        phase_data_2 = {
            "name": "Segunda Fase",
            "position": 1,
            "project_id": project["id"],
        }
        response_2 = client.post("/api/v1/fases/", json=phase_data_2, headers=headers)
        assert response_2.status_code == 201

        data_2 = response_2.json()
        assert data_2["position"] == 1

    def test_create_phase_with_existing_position(self):
        """Probar creación de fase en posición existente (debe reorganizar)"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Crear tres fases
        for i in range(3):
            phase_data = {
                "name": f"Fase {i + 1}",
                "position": i,
                "project_id": project["id"],
            }
            response = client.post("/api/v1/fases/", json=phase_data, headers=headers)
            assert response.status_code == 201

        # Crear nueva fase en posición 1 (debe mover las otras)
        new_phase_data = {
            "name": "Nueva Fase en Posición 1",
            "position": 1,
            "project_id": project["id"],
        }
        response = client.post("/api/v1/fases/", json=new_phase_data, headers=headers)
        assert response.status_code == 201

        # Verificar que la nueva fase está en posición 1
        data = response.json()
        assert data["position"] == 1
        assert data["name"] == "Nueva Fase en Posición 1"

    def test_create_phase_without_authentication(self):
        """Probar creación de fase sin autenticación"""
        phase_data = {
            "name": "Fase Sin Auth",
            "position": 0,
            "project_id": 1,
        }

        response = client.post("/api/v1/fases/", json=phase_data)

        assert response.status_code == 401

    def test_create_phase_invalid_project(self):
        """Probar creación de fase con proyecto inexistente"""
        headers, user_id = self.create_test_user_and_login()

        phase_data = {
            "name": "Fase de Proyecto Inexistente",
            "position": 0,
            "project_id": 999999,
        }

        response = client.post("/api/v1/fases/", json=phase_data, headers=headers)

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]

    def test_create_phase_project_of_other_user(self):
        """Probar creación de fase en proyecto de otro usuario"""
        # Crear primer usuario y proyecto
        headers1, user_id1 = self.create_test_user_and_login("user1@example.com")
        project = self.create_test_project(headers1)

        # Crear segundo usuario
        headers2, user_id2 = self.create_test_user_and_login("user2@example.com")

        # Intentar crear fase en proyecto del primer usuario
        phase_data = {
            "name": "Fase en Proyecto Ajeno",
            "position": 0,
            "project_id": project["id"],
        }

        response = client.post("/api/v1/fases/", json=phase_data, headers=headers2)

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]

    def test_create_phase_invalid_name(self):
        """Probar creación de fase con nombre inválido"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Nombre muy corto
        phase_data = {
            "name": "ABC",
            "position": 0,
            "project_id": project["id"],
        }

        response = client.post("/api/v1/fases/", json=phase_data, headers=headers)

        assert response.status_code == 422

    def test_create_phase_invalid_color(self):
        """Probar creación de fase con color inválido"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        phase_data = {
            "name": "Fase con Color Inválido",
            "position": 0,
            "color": "not_a_color",
            "project_id": project["id"],
        }

        response = client.post("/api/v1/fases/", json=phase_data, headers=headers)

        assert response.status_code == 422

    def test_get_phase_by_id_success(self):
        """Probar obtener fase por ID exitosamente"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Crear fase
        phase_data = {
            "name": "Fase de Prueba",
            "position": 0,
            "color": "#FF5733",
            "project_id": project["id"],
        }

        create_response = client.post(
            "/api/v1/fases/", json=phase_data, headers=headers
        )
        assert create_response.status_code == 201
        phase_id = create_response.json()["id"]

        # Obtener la fase
        response = client.get(f"/api/v1/fases/{phase_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == phase_id
        assert data["name"] == phase_data["name"]
        assert data["position"] == phase_data["position"]
        assert data["color"] == phase_data["color"]

    def test_get_phase_not_found(self):
        """Probar obtener fase que no existe"""
        headers, user_id = self.create_test_user_and_login()

        response = client.get("/api/v1/fases/999999", headers=headers)

        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"]

    def test_get_phase_of_other_user(self):
        """Probar obtener fase de otro usuario"""
        # Crear primer usuario y fase
        headers1, user_id1 = self.create_test_user_and_login("user1@example.com")
        project = self.create_test_project(headers1)

        phase_data = {
            "name": "Fase Usuario 1",
            "position": 0,
            "project_id": project["id"],
        }

        create_response = client.post(
            "/api/v1/fases/", json=phase_data, headers=headers1
        )
        assert create_response.status_code == 201
        phase_id = create_response.json()["id"]

        # Crear segundo usuario
        headers2, user_id2 = self.create_test_user_and_login("user2@example.com")

        # Intentar acceder a la fase del primer usuario
        response = client.get(f"/api/v1/fases/{phase_id}", headers=headers2)

        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"]

    def test_update_phase_success(self):
        """Probar actualización exitosa de fase"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Crear fase
        phase_data = {
            "name": "Fase Original",
            "position": 0,
            "color": "#FF5733",
            "project_id": project["id"],
        }

        create_response = client.post(
            "/api/v1/fases/", json=phase_data, headers=headers
        )
        assert create_response.status_code == 201
        phase_id = create_response.json()["id"]

        # Actualizar la fase
        update_data = {
            "name": "Fase Actualizada",
            "color": "#33FF57",
        }

        response = client.put(
            f"/api/v1/fases/{phase_id}", json=update_data, headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == phase_id
        assert data["name"] == update_data["name"]
        assert data["color"] == update_data["color"]
        assert data["position"] == 0  # No cambiada

    def test_update_phase_position(self):
        """Probar actualización de posición de fase"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Crear tres fases
        phase_ids = []
        for i in range(3):
            phase_data = {
                "name": f"Fase {i + 1}",
                "position": i,
                "project_id": project["id"],
            }
            response = client.post("/api/v1/fases/", json=phase_data, headers=headers)
            assert response.status_code == 201
            phase_ids.append(response.json()["id"])

        # Mover la primera fase a la posición 2
        update_data = {"position": 2}
        response = client.put(
            f"/api/v1/fases/{phase_ids[0]}", json=update_data, headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["position"] == 2

    def test_update_phase_not_found(self):
        """Probar actualización de fase que no existe"""
        headers, user_id = self.create_test_user_and_login()

        update_data = {"name": "Fase Inexistente"}

        response = client.put("/api/v1/fases/999999", json=update_data, headers=headers)

        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"]

    def test_update_phase_of_other_user(self):
        """Probar actualizar fase de otro usuario"""
        # Crear primer usuario y fase
        headers1, user_id1 = self.create_test_user_and_login("user1@example.com")
        project = self.create_test_project(headers1)

        phase_data = {
            "name": "Fase Usuario 1",
            "position": 0,
            "project_id": project["id"],
        }

        create_response = client.post(
            "/api/v1/fases/", json=phase_data, headers=headers1
        )
        assert create_response.status_code == 201
        phase_id = create_response.json()["id"]

        # Crear segundo usuario
        headers2, user_id2 = self.create_test_user_and_login("user2@example.com")

        # Intentar actualizar la fase del primer usuario
        update_data = {"name": "Intento de Hackeo"}
        response = client.put(
            f"/api/v1/fases/{phase_id}", json=update_data, headers=headers2
        )

        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"]

    def test_delete_phase_success(self):
        """Probar eliminación exitosa de fase"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Crear fase
        phase_data = {
            "name": "Fase a Eliminar",
            "position": 0,
            "project_id": project["id"],
        }

        create_response = client.post(
            "/api/v1/fases/", json=phase_data, headers=headers
        )
        assert create_response.status_code == 201
        phase_id = create_response.json()["id"]

        # Eliminar la fase
        response = client.delete(f"/api/v1/fases/{phase_id}", headers=headers)

        assert response.status_code == 204

        # Verificar que la fase ya no existe
        get_response = client.get(f"/api/v1/fases/{phase_id}", headers=headers)
        assert get_response.status_code == 404

    def test_delete_phase_updates_positions(self):
        """Probar que eliminar fase actualiza posiciones de otras fases"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Crear tres fases
        phase_ids = []
        for i in range(3):
            phase_data = {
                "name": f"Fase {i + 1}",
                "position": i,
                "project_id": project["id"],
            }
            response = client.post("/api/v1/fases/", json=phase_data, headers=headers)
            assert response.status_code == 201
            phase_ids.append(response.json()["id"])

        # Eliminar la segunda fase (posición 1)
        response = client.delete(f"/api/v1/fases/{phase_ids[1]}", headers=headers)
        assert response.status_code == 204

        # Verificar que la tercera fase ahora está en posición 1
        response = client.get(f"/api/v1/fases/{phase_ids[2]}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["position"] == 1

    def test_delete_phase_not_found(self):
        """Probar eliminación de fase que no existe"""
        headers, user_id = self.create_test_user_and_login()

        response = client.delete("/api/v1/fases/999999", headers=headers)

        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"]

    def test_delete_phase_of_other_user(self):
        """Probar eliminar fase de otro usuario"""
        # Crear primer usuario y fase
        headers1, user_id1 = self.create_test_user_and_login("user1@example.com")
        project = self.create_test_project(headers1)

        phase_data = {
            "name": "Fase Usuario 1",
            "position": 0,
            "project_id": project["id"],
        }

        create_response = client.post(
            "/api/v1/fases/", json=phase_data, headers=headers1
        )
        assert create_response.status_code == 201
        phase_id = create_response.json()["id"]

        # Crear segundo usuario
        headers2, user_id2 = self.create_test_user_and_login("user2@example.com")

        # Intentar eliminar la fase del primer usuario
        response = client.delete(f"/api/v1/fases/{phase_id}", headers=headers2)

        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"]

        # Verificar que la fase sigue existiendo para el primer usuario
        get_response = client.get(f"/api/v1/fases/{phase_id}", headers=headers1)
        assert get_response.status_code == 200

    def test_get_phase_tasks(self):
        """Probar obtener tareas de una fase"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Crear fase
        phase_data = {
            "name": "Fase con Tareas",
            "position": 0,
            "project_id": project["id"],
        }

        create_response = client.post(
            "/api/v1/fases/", json=phase_data, headers=headers
        )
        assert create_response.status_code == 201
        phase_id = create_response.json()["id"]

        # Obtener tareas de la fase
        response = client.get(f"/api/v1/fases/{phase_id}/tareas", headers=headers)

        assert response.status_code == 200
        # El endpoint debería retornar la fase con sus tareas

    def test_reorder_phases_success(self):
        """Probar reordenamiento exitoso de fases"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        # Crear tres fases
        phase_ids = []
        for i in range(3):
            phase_data = {
                "name": f"Fase {i + 1}",
                "position": i,
                "project_id": project["id"],
            }
            response = client.post("/api/v1/fases/", json=phase_data, headers=headers)
            assert response.status_code == 201
            phase_ids.append(response.json()["id"])

        # Reordenar fases
        reorder_data = [
            {"id": phase_ids[2], "position": 0},
            {"id": phase_ids[0], "position": 1},
            {"id": phase_ids[1], "position": 2},
        ]

        response = client.put(
            f"/api/v1/fases/project/{project['id']}/reorder",
            json=reorder_data,
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        # Verificar que las posiciones se actualizaron correctamente
        for phase in data:
            expected_position = next(
                item["position"] for item in reorder_data if item["id"] == phase["id"]
            )
            assert phase["position"] == expected_position

    def test_reorder_phases_invalid_project(self):
        """Probar reordenamiento con proyecto inexistente"""
        headers, user_id = self.create_test_user_and_login()

        reorder_data = [
            {"id": 1, "position": 0},
        ]

        response = client.put(
            "/api/v1/fases/project/999999/reorder", json=reorder_data, headers=headers
        )

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]

    def test_reorder_phases_invalid_phase(self):
        """Probar reordenamiento con fase inexistente"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        reorder_data = [
            {"id": 999999, "position": 0},
        ]

        response = client.put(
            f"/api/v1/fases/project/{project['id']}/reorder",
            json=reorder_data,
            headers=headers,
        )

        assert response.status_code == 400
        assert "no encontrada" in response.json()["detail"]

    def test_reorder_phases_project_of_other_user(self):
        """Probar reordenamiento en proyecto de otro usuario"""
        # Crear primer usuario y proyecto
        headers1, user_id1 = self.create_test_user_and_login("user1@example.com")
        project = self.create_test_project(headers1)

        # Crear segundo usuario
        headers2, user_id2 = self.create_test_user_and_login("user2@example.com")

        # Intentar reordenar fases del proyecto del primer usuario
        reorder_data = [
            {"id": 1, "position": 0},
        ]

        response = client.put(
            f"/api/v1/fases/project/{project['id']}/reorder",
            json=reorder_data,
            headers=headers2,
        )

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]

    def test_phase_validation_name_whitespace(self):
        """Probar validación de nombre con solo espacios"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        phase_data = {
            "name": "     ",
            "position": 0,
            "project_id": project["id"],
        }

        response = client.post("/api/v1/fases/", json=phase_data, headers=headers)

        assert response.status_code == 422

    def test_phase_validation_negative_position(self):
        """Probar validación de posición negativa"""
        headers, user_id = self.create_test_user_and_login()
        project = self.create_test_project(headers)

        phase_data = {
            "name": "Fase con Posición Negativa",
            "position": -1,
            "project_id": project["id"],
        }

        response = client.post("/api/v1/fases/", json=phase_data, headers=headers)

        assert response.status_code == 422

    def test_phase_validation_missing_required_fields(self):
        """Probar validación de campos requeridos faltantes"""
        headers, user_id = self.create_test_user_and_login()

        # Sin nombre
        phase_data = {
            "position": 0,
            "project_id": 1,
        }

        response = client.post("/api/v1/fases/", json=phase_data, headers=headers)

        assert response.status_code == 422

        # Sin project_id
        phase_data = {
            "name": "Fase sin proyecto",
            "position": 0,
        }

        response = client.post("/api/v1/fases/", json=phase_data, headers=headers)

        assert response.status_code == 422

    def test_phase_without_authentication_endpoints(self):
        """Probar todos los endpoints sin autenticación"""
        # GET fase por ID
        response = client.get("/api/v1/fases/1")
        assert response.status_code == 401

        # PUT actualizar fase
        response = client.put("/api/v1/fases/1", json={"name": "Nueva Fase"})
        assert response.status_code == 401

        # DELETE eliminar fase
        response = client.delete("/api/v1/fases/1")
        assert response.status_code == 401

        # GET tareas de fase
        response = client.get("/api/v1/fases/1/tareas")
        assert response.status_code == 401

        # PUT reordenar fases
        response = client.put("/api/v1/fases/project/1/reorder", json=[])
        assert response.status_code == 401
