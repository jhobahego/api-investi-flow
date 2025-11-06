"""Tests para los endpoints del asistente de IA"""

from unittest.mock import patch

import pytest
from fastapi import status

from app.database import Base
from app.services.ai_service import AIServiceError, ModelNotAvailableError
from tests.test_db_config import client, engine


@pytest.fixture(autouse=True)
def setup_database():
    """Configurar base de datos para cada test"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def create_test_user_and_login():
    """Helper para crear un usuario de prueba y hacer login"""
    user_data = {
        "email": "testuser@example.com",
        "full_name": "Test User",
        "password": "Test123456",
        "phone_number": "+573001234567",
    }

    # Crear usuario
    register_response = client.post("/api/v1/auth/register", json=user_data)
    assert register_response.status_code == 201

    # Hacer login
    login_data = {"username": "testuser@example.com", "password": "Test123456"}
    login_response = client.post("/api/v1/auth/login", data=login_data)
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = register_response.json()["id"]

    return headers, user_id


def create_test_project(headers):
    """Helper para crear un proyecto de prueba"""
    project_data = {
        "name": "Test AI Project",
        "description": "Proyecto para probar el asistente IA",
        "research_type": "experimental",
        "institution": "Universidad Test",
        "status": "in_progress",
    }

    response = client.post("/api/v1/proyectos/", json=project_data, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


class TestSuggestions:
    """Tests para el endpoint de sugerencias de texto"""

    @patch("app.services.ai_service.ai_service.suggest_text")
    def test_generate_suggestion_success(self, mock_suggest_text):
        """Probar generación exitosa de sugerencia"""
        headers, _ = create_test_user_and_login()

        mock_suggest_text.return_value = (
            "Esta es una sugerencia de texto generada por IA.",
            "gemini-1.5-flash",
        )

        response = client.post(
            "/api/v1/ia/sugerencias",
            json={
                "text": "El machine learning es",
                "document_content": "# Introducción\nEl machine learning es",
                "bibliography": [],
                "project_info": {"name": "Test Project"},
            },
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "suggestion" in data
        assert "model_used" in data
        assert data["suggestion"] == "Esta es una sugerencia de texto generada por IA."
        assert data["model_used"] == "gemini-1.5-flash"
        mock_suggest_text.assert_called_once()

    @patch("app.services.ai_service.ai_service.suggest_text")
    def test_generate_suggestion_with_bibliography(self, mock_suggest_text):
        """Probar sugerencia con bibliografía"""
        headers, _ = create_test_user_and_login()

        mock_suggest_text.return_value = (
            "Según Smith (2020), el machine learning...",
            "gemini-1.5-flash",
        )

        response = client.post(
            "/api/v1/ia/sugerencias",
            json={
                "text": "El machine learning",
                "document_content": "Documento completo",
                "bibliography": [
                    {
                        "titulo": "Machine Learning Basics",
                        "autores": "Smith, J.",
                        "anio": 2020,
                        "tipo": "articulo",
                    }
                ],
            },
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "suggestion" in data
        assert "model_used" in data

    @patch("app.services.ai_service.ai_service.suggest_text")
    def test_generate_suggestion_ai_error(self, mock_suggest_text):
        """Probar manejo de error del servicio de IA"""
        headers, _ = create_test_user_and_login()

        mock_suggest_text.side_effect = AIServiceError("Error del servicio")

        response = client.post(
            "/api/v1/ia/sugerencias",
            json={
                "text": "Test",
                "document_content": "Test document",
            },
            headers=headers,
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "ai_service_error"

    def test_generate_suggestion_unauthorized(self):
        """Probar acceso sin autenticación"""
        response = client.post(
            "/api/v1/ia/sugerencias",
            json={
                "text": "Test",
                "document_content": "Test document",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestCitations:
    """Tests para el endpoint de formateo de citas"""

    @patch("app.services.ai_service.ai_service.format_citation")
    def test_format_citation_success(self, mock_format_citation):
        """Probar formateo exitoso de cita"""
        headers, _ = create_test_user_and_login()
        project_id = create_test_project(headers)

        mock_format_citation.return_value = (
            "Smith, J. (2020). Machine Learning Basics. Editorial Académica.",
            "gemini-1.5-flash",
        )

        response = client.post(
            f"/api/v1/ia/proyectos/{project_id}/ia/citas",
            json={
                "tipo": "libro",
                "autores": [{"nombre": "John", "apellido": "Smith"}],
                "anio": 2020,
                "titulo": "Machine Learning Basics",
                "editorial": "Editorial Académica",
            },
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "citation" in data
        assert "model_used" in data
        assert data["model_used"] == "gemini-1.5-flash"
        mock_format_citation.assert_called_once()

    def test_format_citation_project_not_found(self):
        """Probar formateo de cita con proyecto no encontrado"""
        headers, _ = create_test_user_and_login()

        response = client.post(
            "/api/v1/ia/proyectos/99999/ia/citas",
            json={
                "tipo": "libro",
                "autores": [{"nombre": "John", "apellido": "Smith"}],
                "anio": 2020,
                "titulo": "Test Book",
                "editorial": "Test Publisher",
            },
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("app.services.ai_service.ai_service.format_citation")
    def test_format_citation_with_article(self, mock_format_citation):
        """Probar formateo de cita de artículo"""
        headers, _ = create_test_user_and_login()
        project_id = create_test_project(headers)

        mock_format_citation.return_value = (
            "Smith, J. (2020). ML Article. Journal of AI, 10(2), 123-145.",
            "gemini-1.5-flash",
        )

        response = client.post(
            f"/api/v1/ia/proyectos/{project_id}/ia/citas",
            json={
                "tipo": "articulo",
                "autores": [{"nombre": "John", "apellido": "Smith"}],
                "anio": 2020,
                "titulo": "ML Article",
                "revista": "Journal of AI",
                "volumen": "10",
                "numero": "2",
                "paginas": "123-145",
            },
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "citation" in data
        assert "model_used" in data

    def test_format_citation_unauthorized(self):
        """Probar formateo sin autenticación"""
        response = client.post(
            "/api/v1/ia/proyectos/1/ia/citas",
            json={
                "tipo": "libro",
                "autores": [{"nombre": "John", "apellido": "Smith"}],
                "anio": 2020,
                "titulo": "Test Book",
                "editorial": "Test Publisher",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestBibliography:
    """Tests para el endpoint de búsqueda bibliográfica"""

    @patch("app.services.ai_service.ai_service.search_bibliography")
    def test_search_bibliography_success(self, mock_search_bib):
        """Probar búsqueda bibliográfica exitosa"""
        headers, _ = create_test_user_and_login()
        project_id = create_test_project(headers)

        mock_search_bib.return_value = (
            [
                {
                    "titulo": "Machine Learning in Education",
                    "autores": ["Smith", "Jones"],
                    "anio": 2020,
                    "tipo": "articulo",
                    "fuente": "Journal of AI",
                    "doi": "10.1234/test",
                    "url": "https://example.com/article",
                    "resumen": "Este artículo trata sobre...",
                    "relevancia": 5,
                }
            ],
            "gemini-1.5-pro",
        )

        response = client.post(
            f"/api/v1/ia/proyectos/{project_id}/ia/bibliografias",
            json={
                "query": "machine learning in education",
                "max_results": 10,
            },
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "sources" in data
        assert "model_used" in data
        assert "total_found" in data
        assert len(data["sources"]) == 1
        assert data["sources"][0]["titulo"] == "Machine Learning in Education"
        assert data["model_used"] == "gemini-1.5-pro"
        assert data["total_found"] == 1

    def test_search_bibliography_project_not_found(self):
        """Probar búsqueda con proyecto no encontrado"""
        headers, _ = create_test_user_and_login()

        response = client.post(
            "/api/v1/ia/proyectos/99999/ia/bibliografias",
            json={
                "query": "test query",
                "max_results": 5,
            },
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("app.services.ai_service.ai_service.search_bibliography")
    def test_search_bibliography_feature_not_available(self, mock_search_bib):
        """Probar búsqueda con funcionalidad no disponible"""
        headers, _ = create_test_user_and_login()
        project_id = create_test_project(headers)

        mock_search_bib.side_effect = ModelNotAvailableError(
            "Funcionalidad no disponible"
        )

        response = client.post(
            f"/api/v1/ia/proyectos/{project_id}/ia/bibliografias",
            json={
                "query": "test query",
                "max_results": 5,
            },
            headers=headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "feature_not_available"

    @patch("app.services.ai_service.ai_service.search_bibliography")
    def test_search_bibliography_empty_results(self, mock_search_bib):
        """Probar búsqueda sin resultados"""
        headers, _ = create_test_user_and_login()
        project_id = create_test_project(headers)

        mock_search_bib.return_value = ([], "gemini-1.5-pro")

        response = client.post(
            f"/api/v1/ia/proyectos/{project_id}/ia/bibliografias",
            json={
                "query": "very obscure topic that doesnt exist",
                "max_results": 10,
            },
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["sources"] == []
        assert data["total_found"] == 0

    def test_search_bibliography_unauthorized(self):
        """Probar búsqueda sin autenticación"""
        response = client.post(
            "/api/v1/ia/proyectos/1/ia/bibliografias",
            json={
                "query": "test query",
                "max_results": 5,
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestConversations:
    """Tests para los endpoints de conversaciones con historial"""

    def test_list_conversations_empty(self):
        """Probar listado de conversaciones cuando no hay ninguna"""
        headers, _ = create_test_user_and_login()
        project_id = create_test_project(headers)

        response = client.get(
            f"/api/v1/ia/proyectos/{project_id}/conversaciones",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @patch("app.services.ai_service.ai_service.chat")
    def test_chat_create_new_conversation(self, mock_chat):
        """Probar creación de nueva conversación en chat"""
        headers, _ = create_test_user_and_login()
        project_id = create_test_project(headers)

        mock_chat.return_value = (
            "Esta es la respuesta del asistente",
            "gemini-1.5-pro",
        )

        response = client.post(
            f"/api/v1/ia/proyectos/{project_id}/chat",
            json={
                "message": "Hola, ¿cómo estás?",
                "title": "Mi primera conversación",
            },
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "response" in data
        assert "conversation_id" in data
        assert "model_used" in data
        assert "message_id" in data
        assert data["response"] == "Esta es la respuesta del asistente"
        assert data["model_used"] == "gemini-1.5-pro"
        assert isinstance(data["conversation_id"], int)

    @patch("app.services.ai_service.ai_service.chat")
    def test_chat_continue_existing_conversation(self, mock_chat):
        """Probar continuar una conversación existente"""
        headers, _ = create_test_user_and_login()
        project_id = create_test_project(headers)

        # Crear primera conversación
        mock_chat.return_value = ("Primera respuesta", "gemini-1.5-pro")
        response1 = client.post(
            f"/api/v1/ia/proyectos/{project_id}/chat",
            json={"message": "Primer mensaje", "title": "Test Conversation"},
            headers=headers,
        )
        conversation_id = response1.json()["conversation_id"]

        # Continuar la conversación
        mock_chat.return_value = ("Segunda respuesta", "gemini-1.5-pro")
        response2 = client.post(
            f"/api/v1/ia/proyectos/{project_id}/chat",
            json={"message": "Segundo mensaje", "conversation_id": conversation_id},
            headers=headers,
        )

        assert response2.status_code == status.HTTP_200_OK
        data = response2.json()
        assert data["conversation_id"] == conversation_id
        assert data["response"] == "Segunda respuesta"

    @patch("app.services.ai_service.ai_service.chat")
    def test_list_conversations_after_creation(self, mock_chat):
        """Probar listado después de crear conversaciones"""
        headers, _ = create_test_user_and_login()
        project_id = create_test_project(headers)

        # Crear dos conversaciones
        mock_chat.return_value = ("Respuesta", "gemini-1.5-pro")
        client.post(
            f"/api/v1/ia/proyectos/{project_id}/chat",
            json={"message": "Mensaje 1", "title": "Conversación 1"},
            headers=headers,
        )
        client.post(
            f"/api/v1/ia/proyectos/{project_id}/chat",
            json={"message": "Mensaje 2", "title": "Conversación 2"},
            headers=headers,
        )

        # Listar conversaciones
        response = client.get(
            f"/api/v1/ia/proyectos/{project_id}/conversaciones",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert all("title" in conv for conv in data)
        assert all("message_count" in conv for conv in data)

    def test_chat_project_not_found(self):
        """Probar chat con proyecto no encontrado"""
        headers, _ = create_test_user_and_login()

        response = client.post(
            "/api/v1/ia/proyectos/99999/chat",
            json={"message": "Test message"},
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_chat_unauthorized(self):
        """Probar chat sin autenticación"""
        response = client.post(
            "/api/v1/ia/proyectos/1/chat",
            json={"message": "Test message"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.services.ai_service.ai_service.chat")
    def test_get_conversation_with_messages(self, mock_chat):
        """Probar obtener una conversación específica con sus mensajes"""
        headers, _ = create_test_user_and_login()
        project_id = create_test_project(headers)

        # Crear conversación con mensajes
        mock_chat.return_value = ("Respuesta", "gemini-1.5-pro")
        response = client.post(
            f"/api/v1/ia/proyectos/{project_id}/chat",
            json={"message": "Hola", "title": "Test"},
            headers=headers,
        )
        conversation_id = response.json()["conversation_id"]

        # Obtener conversación
        response = client.get(
            f"/api/v1/ia/proyectos/{project_id}/conversaciones/{conversation_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == conversation_id
        assert data["title"] == "Test"
        assert "messages" in data
        assert len(data["messages"]) >= 2  # Mensaje del usuario + respuesta

    @patch("app.services.ai_service.ai_service.chat")
    def test_update_conversation_title(self, mock_chat):
        """Probar actualizar el título de una conversación"""
        headers, _ = create_test_user_and_login()
        project_id = create_test_project(headers)

        # Crear conversación
        mock_chat.return_value = ("Respuesta", "gemini-1.5-pro")
        response = client.post(
            f"/api/v1/ia/proyectos/{project_id}/chat",
            json={"message": "Hola", "title": "Título Original"},
            headers=headers,
        )
        conversation_id = response.json()["conversation_id"]

        # Actualizar título
        response = client.patch(
            f"/api/v1/ia/proyectos/{project_id}/conversaciones/{conversation_id}",
            json={"title": "Título Actualizado"},
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Título Actualizado"

    @patch("app.services.ai_service.ai_service.chat")
    def test_delete_conversation(self, mock_chat):
        """Probar eliminar una conversación"""
        headers, _ = create_test_user_and_login()
        project_id = create_test_project(headers)

        # Crear conversación
        mock_chat.return_value = ("Respuesta", "gemini-1.5-pro")
        response = client.post(
            f"/api/v1/ia/proyectos/{project_id}/chat",
            json={"message": "Hola", "title": "Para eliminar"},
            headers=headers,
        )
        conversation_id = response.json()["conversation_id"]

        # Eliminar conversación
        response = client.delete(
            f"/api/v1/ia/proyectos/{project_id}/conversaciones/{conversation_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verificar que ya no existe
        response = client.get(
            f"/api/v1/ia/proyectos/{project_id}/conversaciones/{conversation_id}",
            headers=headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
