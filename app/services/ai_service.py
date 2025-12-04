import json
import logging
from typing import Any

from google import genai
from google.genai import types

from app.core.ai_config import (
    AIFeature,
    UserPlan,
    get_generation_config,
    get_model_for_feature,
    is_feature_available,
)
from app.core.ai_prompts import (
    BIBLIOGRAPHY_SYSTEM_PROMPT,
    CHAT_SYSTEM_PROMPT,
    CITATIONS_SYSTEM_PROMPT,
    SUGGESTIONS_SYSTEM_PROMPT,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Excepción base para errores del servicio de IA"""

    pass


class ModelNotAvailableError(AIServiceError):
    """Excepción cuando un modelo no está disponible para el plan del usuario"""

    pass


class AIService:
    """
    Servicio para operaciones de IA con Google Gemini.
    """

    def __init__(self):
        """Inicializa el servicio de IA con la API de Gemini"""
        if not settings.GOOGLE_AI_API_KEY:
            raise AIServiceError(
                "GOOGLE_AI_API_KEY no está configurada en las variables de entorno"
            )

        # Inicializar el cliente de Gemini con la nueva API
        self.client = genai.Client(api_key=settings.GOOGLE_AI_API_KEY)

        # Configuración de seguridad usando la nueva API
        self.safety_settings = [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
        ]

        logger.info("AIService inicializado correctamente con google-genai")

    def _get_config(
        self,
        feature: AIFeature,
        plan: UserPlan = UserPlan.PROFESIONAL,
        use_grounding: bool = False,
    ) -> tuple[str, types.GenerateContentConfig]:
        """
        Obtiene la configuración para generar contenido con Gemini.

        Args:
            feature: La funcionalidad de IA solicitada
            plan: El plan del usuario (por defecto PROFESIONAL para desarrollo)
            use_grounding: Si se debe activar Google Search Grounding

        Returns:
            tuple[str, GenerateContentConfig]: (nombre del modelo, configuración)

        Raises:
            ModelNotAvailableError: Si el modelo no está disponible para el plan
            AIServiceError: Si hay un error al crear la configuración
        """
        try:
            if not is_feature_available(feature, plan):
                raise ModelNotAvailableError(
                    f"La funcionalidad '{feature.value}' no está disponible "
                    f"para el plan '{plan.value}'"
                )

            model_name = get_model_for_feature(feature, plan)
            if not model_name:
                raise ModelNotAvailableError(
                    f"No hay modelo disponible para '{feature.value}' con plan '{plan.value}'"
                )

            generation_config_dict = get_generation_config(model_name, feature)

            # Crear la configuración base con overrides específicos de funcionalidad
            config = types.GenerateContentConfig(
                temperature=generation_config_dict.get("temperature", 0.7),
                top_p=generation_config_dict.get("top_p", 0.95),
                top_k=generation_config_dict.get("top_k", 40),
                max_output_tokens=generation_config_dict.get("max_output_tokens", 2048),
                safety_settings=self.safety_settings,
            )

            # Agregar herramienta de Grounding si se solicita
            if use_grounding:
                grounding_tool = types.Tool(google_search=types.GoogleSearch())
                config.tools = [grounding_tool]
                logger.info(f"Grounding habilitado para modelo '{model_name}'")

            logger.info(
                f"Configuración creada para modelo '{model_name}' (feature: '{feature.value}')"
            )
            return model_name, config

        except ValueError as e:
            raise ModelNotAvailableError(str(e))
        except Exception as e:
            logger.error(f"Error al crear configuración: {str(e)}")
            raise AIServiceError(
                f"Error al inicializar la configuración de IA: {str(e)}"
            )

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]],
        project_context: str | None = None,
        plan: UserPlan = UserPlan.PROFESIONAL,
    ) -> tuple[str, str]:
        """
        Realiza una conversación con el asistente de IA en el contexto de un proyecto.

        Args:
            message: El mensaje del usuario
            history: Historial de mensajes previos
            project_context: Contexto del proyecto formateado
            plan: Plan del usuario (por defecto PROFESIONAL)

        Returns:
            tuple[str, str]: (respuesta del modelo, nombre del modelo usado)

        Raises:
            AIServiceError: Si hay un error en la comunicación con la API
        """
        try:
            model_name, config = self._get_config(AIFeature.CHAT, plan)

            # Formatear el prompt del sistema con el contexto del proyecto
            system_prompt = CHAT_SYSTEM_PROMPT.format(
                project_context=project_context
                or "No hay información específica del proyecto disponible."
            )

            # Construir el contenido con historial y mensaje actual
            contents = []

            # Agregar historial formateado
            for msg in history:
                contents.append(msg.get("content", ""))

            # Agregar mensaje actual
            contents.append(message)

            # Generar respuesta usando system_instruction
            response = self.client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=config.temperature,
                    top_p=config.top_p,
                    top_k=config.top_k,
                    max_output_tokens=config.max_output_tokens,
                    safety_settings=config.safety_settings,
                    system_instruction=system_prompt,
                ),
            )

            logger.info(f"Chat completado exitosamente con {model_name}")

            if not response.text:
                raise AIServiceError("No se recibió respuesta del modelo")

            return response.text, model_name

        except ModelNotAvailableError:
            raise
        except Exception as e:
            logger.error(f"Error en chat: {str(e)}")
            raise AIServiceError(f"Error al procesar la conversación: {str(e)}")

    async def suggest_text(
        self,
        text: str,
        document_content: str,
        bibliography: list[dict] | None = None,
        project_context: str | None = None,
        plan: UserPlan = UserPlan.ESTUDIANTE,
    ) -> tuple[str, str]:
        """
        Genera sugerencias de autocompletado de texto basadas en el contexto completo.

        Args:
            text: El texto actual donde el usuario solicita sugerencia
            document_content: Contenido completo del documento
            bibliography: Lista de referencias bibliográficas del proyecto
            project_context: Contexto del proyecto formateado
            plan: Plan del usuario (por defecto ESTUDIANTE)

        Returns:
            tuple[str, str]: (sugerencia de texto, nombre del modelo usado)

        Raises:
            AIServiceError: Si hay un error en la comunicación con la API
        """
        try:
            from app.core.ai_prompts import (
                format_bibliography_context,
                format_document_content,
            )

            model_name, config = self._get_config(AIFeature.SUGGESTIONS, plan)

            # Formatear contextos
            project_ctx = project_context or "Proyecto sin información específica"
            bibliography_ctx = format_bibliography_context(bibliography)
            document_ctx = format_document_content(document_content)

            # Construir el prompt con todos los contextos
            prompt = SUGGESTIONS_SYSTEM_PROMPT.format(
                project_context=project_ctx,
                bibliography_context=bibliography_ctx,
                document_content=document_ctx,
            )

            # Agregar el texto actual al final
            prompt += f"\n\nTEXTO DONDE CONTINUAR:\n{text}\n\nTU SUGERENCIA:"

            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            if not response.text:
                raise AIServiceError("No se recibió sugerencia de texto del modelo")

            suggestion = response.text.strip()

            logger.info(f"Sugerencia generada exitosamente con {model_name}")
            return suggestion, model_name

        except ModelNotAvailableError:
            raise
        except Exception as e:
            logger.error(f"Error en sugerencias: {str(e)}")
            raise AIServiceError(f"Error al generar sugerencias: {str(e)}")

    async def format_citation(
        self,
        citation_data: dict[str, Any],
        project_bibliography: list[dict] | None = None,
        project_context: str | None = None,
        plan: UserPlan = UserPlan.ESTUDIANTE,
    ) -> tuple[str, str]:
        """
        Formatea una cita bibliográfica en estilo APA 7 considerando el contexto del proyecto.

        Args:
            citation_data: Datos de la fuente (tipo, autores, año, etc.)
            project_bibliography: Bibliografía existente en el proyecto
            project_context: Contexto del proyecto formateado
            plan: Plan del usuario (por defecto ESTUDIANTE)

        Returns:
            tuple[str, str]: (cita formateada, nombre del modelo usado)

        Raises:
            AIServiceError: Si hay un error en la comunicación con la API
        """
        try:
            from app.core.ai_prompts import format_bibliography_context

            model_name, config = self._get_config(AIFeature.CITATIONS, plan)

            # Formatear contextos
            project_ctx = project_context or "Proyecto sin información específica"
            bibliography_ctx = format_bibliography_context(project_bibliography)

            # Construir el prompt con todos los contextos
            citation_json = json.dumps(citation_data, indent=2, ensure_ascii=False)

            prompt = CITATIONS_SYSTEM_PROMPT.format(
                project_context=project_ctx,
                bibliography_context=bibliography_ctx,
                citation_data=citation_json,
            )

            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            if not response.text:
                raise AIServiceError("No se recibió cita formateada del modelo")

            citation = response.text.strip()

            logger.info(f"Cita formateada exitosamente con {model_name}")
            return citation, model_name

        except ModelNotAvailableError:
            raise
        except Exception as e:
            logger.error(f"Error en formateo de cita: {str(e)}")
            raise AIServiceError(f"Error al formatear la cita: {str(e)}")

    async def search_bibliography(
        self,
        query: str,
        max_results: int = 10,
        plan: UserPlan = UserPlan.INVESTIGADOR,
        project_context: str | None = None,
        search_context: str | None = None,
    ) -> tuple[list[dict[str, Any]], str]:
        """
        Busca fuentes bibliográficas relevantes usando Grounding con Google Search.

        Args:
            query: Consulta de búsqueda
            max_results: Número máximo de resultados
            plan: Plan del usuario (por defecto INVESTIGADOR)
            project_context: Contexto del proyecto formateado
            search_context: Contexto adicional de búsqueda

        Returns:
            tuple[list[dict], str]: (lista de fuentes encontradas, nombre del modelo usado)

        Raises:
            AIServiceError: Si hay un error en la comunicación con la API
        """
        try:
            # ACTIVAR GROUNDING para búsqueda bibliográfica
            model_name, config = self._get_config(
                AIFeature.BIBLIOGRAPHY, plan, use_grounding=True
            )

            # Construir contexto adicional
            context_str = ""
            if project_context:
                context_str += f"\nCONTEXTO DEL PROYECTO:\n{project_context}"
            if search_context:
                context_str += (
                    f"\nCONTEXTO DE LA BÚSQUEDA (Documento actual):\n{search_context}"
                )

            # Construir el prompt optimizado para Grounding EN ESPAÑOL
            # Asegurar que la búsqueda siempre se realice en español
            prompt = f"""{BIBLIOGRAPHY_SYSTEM_PROMPT}
            {context_str}

            CONSULTA DE BÚSQUEDA: {query}
            NÚMERO DE RESULTADOS SOLICITADOS: {max_results}
            IDIOMA REQUERIDO: Español (castellano) - OBLIGATORIO
            FORMATO DE RESPUESTA: ÚNICAMENTE JSON VÁLIDO. NO INCLUIR BLOQUES DE CÓDIGO MARKDOWN (```json ... ```). NO INCLUIR HTML.

            INSTRUCCIÓN FINAL: Busca en Google SOLO fuentes académicas en español sobre la consulta anterior, utilizando el contexto proporcionado para refinar la relevancia. Si la consulta está en inglés u otro idioma, tradúcela primero al español para realizar la búsqueda.

            FUENTES EN ESPAÑOL ENCONTRADAS (JSON):"""

            # Generar contenido con Grounding habilitado
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            if not response.text:
                raise AIServiceError("No se recibió respuesta del modelo para búsqueda")

            # Extraer metadata de Grounding (URLs reales verificadas)
            grounding_metadata = getattr(response, "grounding_metadata", None)
            sources = []

            if grounding_metadata:
                logger.info(f"Grounding metadata disponible: {grounding_metadata}")
                # Procesar metadata de Grounding para extraer fuentes reales
                sources = self._parse_grounding_sources(grounding_metadata, max_results)
            else:
                logger.warning(
                    "No se recibió grounding_metadata, intentando parsear respuesta de texto"
                )
                # Fallback: intentar parsear la respuesta como JSON
                sources = self._parse_text_sources(response.text, max_results)

            logger.info(
                f"Búsqueda bibliográfica completada con {model_name} (Grounding activado), {len(sources)} fuentes encontradas"
            )
            return sources, model_name

        except ModelNotAvailableError:
            raise
        except Exception as e:
            logger.error(f"Error en búsqueda bibliográfica: {str(e)}")
            raise AIServiceError(f"Error al buscar bibliografía: {str(e)}")

    def _parse_grounding_sources(
        self, grounding_metadata: Any, max_results: int
    ) -> list[dict[str, Any]]:
        """
        Extrae fuentes bibliográficas reales desde la metadata de Grounding.

        Args:
            grounding_metadata: Metadata de Grounding con URLs y snippets verificados
            max_results: Número máximo de fuentes a retornar

        Returns:
            list[dict]: Lista de fuentes con datos reales verificados
        """
        sources = []

        try:
            # Extraer chunks de Grounding (URLs y snippets reales)
            grounding_chunks = getattr(grounding_metadata, "grounding_chunks", [])
            web_chunks = getattr(grounding_metadata, "web", None)

            if web_chunks:
                chunks_to_process = getattr(web_chunks, "chunks", grounding_chunks)
            else:
                chunks_to_process = grounding_chunks

            for idx, chunk in enumerate(chunks_to_process[:max_results]):
                try:
                    # Extraer URL real verificada
                    url = getattr(chunk, "uri", None) or getattr(chunk, "url", "")
                    title = getattr(chunk, "title", "Fuente académica")
                    snippet = getattr(chunk, "snippet", "") or getattr(
                        chunk, "text", ""
                    )

                    if not url:
                        continue

                    # Intentar extraer metadatos académicos básicos desde snippet/title
                    source_data = {
                        "titulo": title[:200],  # Limitar longitud
                        "autores": [
                            "Autor desconocido"
                        ],  # Google Search no siempre provee autores
                        "anio": 2024,  # Fecha aproximada, se podría mejorar con parsing
                        "tipo": self._infer_source_type(url),
                        "fuente": self._extract_domain(url),
                        "doi": None,  # Google Search rara vez incluye DOI directamente
                        "url": url,
                        "resumen": snippet[:300]
                        if snippet
                        else "Fuente verificada con Google Search",
                        "relevancia": 5
                        - (idx // 2),  # Score basado en posición (5, 5, 4, 4, 3...)
                    }

                    sources.append(source_data)

                except Exception as e:
                    logger.warning(f"Error al procesar chunk de Grounding: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error al parsear grounding_metadata: {str(e)}")

        return sources

    def _parse_text_sources(
        self, response_text: str, max_results: int
    ) -> list[dict[str, Any]]:
        """
        Fallback: parsea fuentes desde texto generado (menos confiable que Grounding).

        Args:
            response_text: Respuesta de texto del modelo
            max_results: Número máximo de fuentes

        Returns:
            list[dict]: Lista de fuentes parseadas
        """
        try:
            # Limpiar la respuesta para obtener solo el JSON
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            sources = json.loads(response_text.strip())

            if not isinstance(sources, list):
                raise ValueError("La respuesta no es una lista válida")

            return sources[:max_results]

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Error al parsear respuesta JSON: {str(e)}")
            return []

    def _infer_source_type(self, url: str) -> str:
        """Infiere el tipo de fuente académica desde la URL."""
        url_lower = url.lower()

        if any(
            domain in url_lower
            for domain in ["scholar.google", "arxiv.org", "pubmed", "ieee.org"]
        ):
            return "articulo"
        elif any(
            domain in url_lower
            for domain in ["springer.com", "wiley.com", "elsevier.com"]
        ):
            return "articulo"
        elif any(
            domain in url_lower for domain in ["books.google", "amazon.com/books"]
        ):
            return "libro"
        elif ".edu" in url_lower or ".ac." in url_lower:
            return "tesis"  # Posiblemente recurso académico/tesis
        else:
            return "web"

    def _extract_domain(self, url: str) -> str:
        """Extrae el dominio limpio desde una URL."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain
        except Exception:
            return "Fuente web"

    def check_api_health(self) -> bool:
        """
        Verifica que la API de Gemini esté funcionando correctamente.

        Returns:
            bool: True si la API responde correctamente, False en caso contrario
        """
        try:
            # Intentar una generación simple como health check
            test_response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents="Hello, test API health check",
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=10,
                ),
            )

            if test_response and test_response.text:
                logger.info("API de Gemini funcionando correctamente")
                return True
            else:
                logger.warning("API respondió pero sin texto")
                return False

        except Exception as e:
            logger.error(f"Error en health check de API: {str(e)}")
            return False


# Instancia global del servicio (singleton)
ai_service = AIService()
