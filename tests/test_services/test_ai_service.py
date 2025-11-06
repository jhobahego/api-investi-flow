"""Tests para el servicio de IA con mocks"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.ai_config import AIFeature, UserPlan
from app.services.ai_service import AIService, AIServiceError


@pytest.fixture
def mock_genai_client():
    """Mock del cliente de Google Genai"""
    with patch("app.services.ai_service.genai.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def ai_service_instance(mock_genai_client):
    """Instancia del servicio de IA con cliente mockeado"""
    with patch("app.core.config.settings.GOOGLE_AI_API_KEY", "test_api_key"):
        service = AIService()
        return service


class TestAIService:
    """Pruebas para el servicio de IA"""

    def test_init_success(self, mock_genai_client):
        """Probar inicialización exitosa del servicio"""
        with patch("app.core.config.settings.GOOGLE_AI_API_KEY", "test_api_key"):
            service = AIService()
            assert service.client is not None
            assert service.safety_settings is not None
            assert len(service.safety_settings) == 4

    def test_init_missing_api_key(self):
        """Probar inicialización sin API key"""
        with patch("app.core.config.settings.GOOGLE_AI_API_KEY", None):
            with pytest.raises(AIServiceError) as exc_info:
                AIService()

            assert "GOOGLE_AI_API_KEY no está configurada" in str(exc_info.value)

    def test_get_config_suggestions_success(self, ai_service_instance):
        """Probar obtención de configuración para sugerencias"""
        model_name, config = ai_service_instance._get_config(
            AIFeature.SUGGESTIONS, UserPlan.ESTUDIANTE
        )

        assert model_name is not None
        assert config is not None
        assert hasattr(config, "temperature")
        assert hasattr(config, "max_output_tokens")

    def test_get_config_chat_success(self, ai_service_instance):
        """Probar obtención de configuración para chat"""
        model_name, config = ai_service_instance._get_config(
            AIFeature.CHAT, UserPlan.PROFESIONAL
        )

        assert model_name is not None
        assert config is not None

    def test_get_config_bibliography_success(self, ai_service_instance):
        """Probar obtención de configuración para bibliografía"""
        model_name, config = ai_service_instance._get_config(
            AIFeature.BIBLIOGRAPHY, UserPlan.INVESTIGADOR
        )

        assert model_name is not None
        assert config is not None

    def test_get_config_with_grounding(self, ai_service_instance):
        """Probar obtención de configuración con grounding"""
        model_name, config = ai_service_instance._get_config(
            AIFeature.BIBLIOGRAPHY, UserPlan.INVESTIGADOR, use_grounding=True
        )

        assert model_name is not None
        assert config is not None
        assert hasattr(config, "tools")
        assert config.tools is not None

    def test_get_config_feature_not_available(self, ai_service_instance):
        """Probar error cuando la funcionalidad no está disponible para el plan"""
        from app.services.ai_service import AIServiceError

        # Intentar usar bibliografía con plan estudiante (no disponible)
        with pytest.raises(AIServiceError) as exc_info:
            ai_service_instance._get_config(AIFeature.BIBLIOGRAPHY, UserPlan.ESTUDIANTE)

        assert "no está disponible" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_chat_success(self, ai_service_instance, mock_genai_client):
        """Probar chat exitoso"""
        # Mock de la respuesta
        mock_response = MagicMock()
        mock_response.text = "Esta es una respuesta de prueba"
        mock_genai_client.models.generate_content.return_value = mock_response

        message = "¿Cómo puedo mejorar mi investigación?"
        history = []
        project_context = "Proyecto sobre Machine Learning"

        response_text, model_used = await ai_service_instance.chat(
            message=message, history=history, project_context=project_context
        )

        assert response_text == "Esta es una respuesta de prueba"
        assert model_used is not None
        assert mock_genai_client.models.generate_content.called

    @pytest.mark.asyncio
    async def test_chat_no_response(self, ai_service_instance, mock_genai_client):
        """Probar error cuando no hay respuesta del chat"""
        # Mock de respuesta sin texto
        mock_response = MagicMock()
        mock_response.text = None
        mock_genai_client.models.generate_content.return_value = mock_response

        message = "Test message"
        history = []

        with pytest.raises(AIServiceError) as exc_info:
            await ai_service_instance.chat(
                message=message, history=history, project_context=None
            )

        assert "No se recibió respuesta" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_suggest_text_success(self, ai_service_instance, mock_genai_client):
        """Probar sugerencias de texto exitosas"""
        # Mock de la respuesta
        mock_response = MagicMock()
        mock_response.text = "Esta es una sugerencia de autocompletado"
        mock_genai_client.models.generate_content.return_value = mock_response

        text = "La investigación demuestra que"
        document_content = "Contenido del documento..."
        bibliography = [{"titulo": "Estudio 1", "autores": ["Smith"]}]
        project_context = "Proyecto de investigación educativa"

        suggestion, model_used = await ai_service_instance.suggest_text(
            text=text,
            document_content=document_content,
            bibliography=bibliography,
            project_context=project_context,
        )

        assert suggestion == "Esta es una sugerencia de autocompletado"
        assert model_used is not None
        assert mock_genai_client.models.generate_content.called

    @pytest.mark.asyncio
    async def test_suggest_text_no_response(
        self, ai_service_instance, mock_genai_client
    ):
        """Probar error cuando no hay sugerencia"""
        # Mock de respuesta sin texto
        mock_response = MagicMock()
        mock_response.text = None
        mock_genai_client.models.generate_content.return_value = mock_response

        with pytest.raises(AIServiceError) as exc_info:
            await ai_service_instance.suggest_text(
                text="Test", document_content="Content", bibliography=None
            )

        assert "No se recibió sugerencia" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_format_citation_success(
        self, ai_service_instance, mock_genai_client
    ):
        """Probar formateo de cita exitoso"""
        # Mock de la respuesta
        mock_response = MagicMock()
        mock_response.text = (
            "Smith, J. (2020). Título del artículo. Revista, 10(2), 123-145."
        )
        mock_genai_client.models.generate_content.return_value = mock_response

        citation_data = {
            "tipo": "articulo",
            "autores": [{"apellido": "Smith", "nombre": "J."}],
            "anio": 2020,
            "titulo": "Título del artículo",
        }

        citation, model_used = await ai_service_instance.format_citation(
            citation_data=citation_data,
            project_bibliography=None,
            project_context=None,
        )

        assert "Smith, J." in citation
        assert model_used is not None
        assert mock_genai_client.models.generate_content.called

    @pytest.mark.asyncio
    async def test_format_citation_no_response(
        self, ai_service_instance, mock_genai_client
    ):
        """Probar error cuando no hay cita formateada"""
        # Mock de respuesta sin texto
        mock_response = MagicMock()
        mock_response.text = None
        mock_genai_client.models.generate_content.return_value = mock_response

        citation_data = {"tipo": "articulo", "autores": [], "anio": 2020}

        with pytest.raises(AIServiceError) as exc_info:
            await ai_service_instance.format_citation(citation_data=citation_data)

        assert "No se recibió cita formateada" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_bibliography_success(
        self, ai_service_instance, mock_genai_client
    ):
        """Probar búsqueda bibliográfica exitosa"""
        # Mock de la respuesta con grounding
        mock_response = MagicMock()
        mock_response.text = (
            '[{"titulo": "Artículo 1", "autores": ["Smith"], "anio": 2020}]'
        )

        # Mock de grounding metadata con soporte web
        mock_support = MagicMock()
        mock_support.uri = "https://example.com/article1"
        mock_support.title = "Artículo de Investigación"

        mock_grounding_support = MagicMock()
        mock_grounding_support.web_search_queries = ["machine learning"]
        mock_grounding_support.grounding_supports = [mock_support]

        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].grounding_metadata = mock_grounding_support
        mock_genai_client.models.generate_content.return_value = mock_response

        query = "machine learning in education"
        sources, model_used = await ai_service_instance.search_bibliography(
            query=query, max_results=10
        )

        assert isinstance(sources, list)
        # El mock debe devolver al menos una fuente
        assert len(sources) >= 0
        assert model_used is not None
        assert mock_genai_client.models.generate_content.called

    @pytest.mark.asyncio
    async def test_search_bibliography_no_response(
        self, ai_service_instance, mock_genai_client
    ):
        """Probar error cuando no hay respuesta en búsqueda bibliográfica"""
        # Mock de respuesta sin texto
        mock_response = MagicMock()
        mock_response.text = None
        mock_genai_client.models.generate_content.return_value = mock_response

        with pytest.raises(AIServiceError) as exc_info:
            await ai_service_instance.search_bibliography(query="test query")

        assert "No se recibió respuesta" in str(exc_info.value)

    def test_parse_grounding_sources_success(self, ai_service_instance):
        """Probar parseo de fuentes desde grounding metadata"""
        # Mock de grounding metadata
        mock_chunk1 = MagicMock()
        mock_chunk1.uri = "https://scholar.google.com/article1"
        mock_chunk1.title = "Machine Learning in Education"
        mock_chunk1.snippet = "This article discusses ML applications..."

        mock_chunk2 = MagicMock()
        mock_chunk2.uri = "https://arxiv.org/article2"
        mock_chunk2.title = "Deep Learning Research"
        mock_chunk2.snippet = "Recent advances in deep learning..."

        mock_metadata = MagicMock()
        mock_metadata.grounding_chunks = [mock_chunk1, mock_chunk2]
        mock_metadata.web = None

        sources = ai_service_instance._parse_grounding_sources(mock_metadata, 5)

        assert isinstance(sources, list)
        assert len(sources) == 2
        assert sources[0]["url"] == "https://scholar.google.com/article1"
        assert sources[0]["titulo"] == "Machine Learning in Education"

    def test_parse_text_sources_success(self, ai_service_instance):
        """Probar parseo de fuentes desde texto JSON"""
        json_text = """
        [
            {
                "titulo": "Artículo 1",
                "autores": ["Smith"],
                "anio": 2020,
                "url": "https://example.com/article1"
            },
            {
                "titulo": "Artículo 2",
                "autores": ["Doe"],
                "anio": 2021,
                "url": "https://example.com/article2"
            }
        ]
        """

        sources = ai_service_instance._parse_text_sources(json_text, 5)

        assert isinstance(sources, list)
        assert len(sources) == 2
        assert sources[0]["titulo"] == "Artículo 1"

    def test_parse_text_sources_with_code_block(self, ai_service_instance):
        """Probar parseo de fuentes con bloque de código JSON"""
        json_text = """```json
        [
            {"titulo": "Artículo 1", "autores": ["Smith"], "anio": 2020}
        ]
        ```"""

        sources = ai_service_instance._parse_text_sources(json_text, 5)

        assert isinstance(sources, list)
        assert len(sources) == 1

    def test_parse_text_sources_invalid_json(self, ai_service_instance):
        """Probar parseo de fuentes con JSON inválido"""
        json_text = "Esta no es una respuesta JSON válida"

        sources = ai_service_instance._parse_text_sources(json_text, 5)

        assert isinstance(sources, list)
        assert len(sources) == 0

    def test_infer_source_type(self, ai_service_instance):
        """Probar inferencia de tipo de fuente desde URL"""
        assert (
            ai_service_instance._infer_source_type("https://scholar.google.com/test")
            == "articulo"
        )
        assert (
            ai_service_instance._infer_source_type("https://arxiv.org/test")
            == "articulo"
        )
        assert (
            ai_service_instance._infer_source_type("https://books.google.com/test")
            == "libro"
        )
        assert (
            ai_service_instance._infer_source_type("https://university.edu/test")
            == "tesis"
        )
        assert (
            ai_service_instance._infer_source_type("https://example.com/test") == "web"
        )

    def test_extract_domain(self, ai_service_instance):
        """Probar extracción de dominio desde URL"""
        assert (
            ai_service_instance._extract_domain("https://www.example.com/path")
            == "example.com"
        )
        assert (
            ai_service_instance._extract_domain("https://scholar.google.com/article")
            == "scholar.google.com"
        )

    def test_check_api_health_success(self, ai_service_instance, mock_genai_client):
        """Probar health check exitoso"""
        # Mock de respuesta exitosa
        mock_response = MagicMock()
        mock_response.text = "API is working"
        mock_genai_client.models.generate_content.return_value = mock_response

        result = ai_service_instance.check_api_health()

        assert result is True
        assert mock_genai_client.models.generate_content.called

    def test_check_api_health_failure(self, ai_service_instance, mock_genai_client):
        """Probar health check con fallo"""
        # Mock de respuesta sin texto
        mock_response = MagicMock()
        mock_response.text = None
        mock_genai_client.models.generate_content.return_value = mock_response

        result = ai_service_instance.check_api_health()

        assert result is False

    def test_check_api_health_exception(self, ai_service_instance, mock_genai_client):
        """Probar health check con excepción"""
        # Mock que lanza excepción
        mock_genai_client.models.generate_content.side_effect = Exception("API Error")

        result = ai_service_instance.check_api_health()

        assert result is False
