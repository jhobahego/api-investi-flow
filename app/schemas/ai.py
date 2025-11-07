from typing import Any

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# SCHEMAS PARA CHAT
# =============================================================================


class ChatMessage(BaseModel):
    """Mensaje individual en el historial del chat"""

    role: str = Field(..., description="Rol del mensaje: 'user' o 'model'")
    content: str = Field(..., description="Contenido del mensaje")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ["user", "model"]:
            raise ValueError("El rol debe ser 'user' o 'model'")
        return v


class ChatRequest(BaseModel):
    """Request para el endpoint de chat"""

    message: str = Field(
        ..., description="Mensaje del usuario", min_length=1, max_length=5000
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Historial de mensajes previos en la conversación",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "¿Cómo puedo estructurar mi marco teórico?",
                    "history": [
                        {
                            "role": "user",
                            "content": "Estoy investigando sobre inteligencia artificial en educación",
                        },
                        {
                            "role": "model",
                            "content": "Es un tema muy interesante. La IA en educación tiene varias aplicaciones...",
                        },
                    ],
                }
            ]
        }
    }


class ChatResponse(BaseModel):
    """Response del endpoint de chat"""

    response: str = Field(..., description="Respuesta del asistente de IA")
    model_used: str = Field(..., description="Modelo de IA utilizado")

    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "examples": [
                {
                    "response": "Para estructurar tu marco teórico sobre IA en educación, te sugiero...",
                    "model_used": "gemini-2.0-flash-thinking-exp",
                }
            ]
        },
    }


# =============================================================================
# SCHEMAS PARA SUGERENCIAS
# =============================================================================


class BibliographyReference(BaseModel):
    """Referencia bibliográfica simplificada para contexto"""

    autores: str = Field(..., description="Autores de la fuente")
    anio: int = Field(..., description="Año de publicación")
    titulo: str = Field(..., description="Título de la fuente")
    tipo: str = Field(..., description="Tipo de fuente (libro, articulo, etc.)")


class SuggestionRequest(BaseModel):
    """Request para el endpoint de sugerencias de texto"""

    text: str = Field(
        ...,
        description="Texto actual donde el usuario solicita la sugerencia",
        min_length=1,
        max_length=1000,
    )
    document_content: str = Field(
        ...,
        description="Contenido completo del documento hasta el momento",
        max_length=20000,
    )
    bibliography: list[BibliographyReference] = Field(
        default_factory=list,
        description="Bibliografía disponible en el proyecto para citaciones",
    )
    project_info: dict[str, Any] | None = Field(
        None, description="Información del proyecto (nombre, descripción, tipo, etc.)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "Los resultados del experimento muestran que",
                    "document_content": "# Introducción\n\nLa inteligencia artificial...\n\n# Metodología\n\n...\n\n# Resultados\n\nLos resultados del experimento muestran que",
                    "bibliography": [
                        {
                            "autores": "García, M. & López, A.",
                            "anio": 2023,
                            "titulo": "IA en educación superior",
                            "tipo": "articulo",
                        }
                    ],
                    "project_info": {
                        "name": "Impacto de la IA en educación",
                        "research_type": "experimental",
                    },
                }
            ]
        }
    }


class SuggestionResponse(BaseModel):
    """Response del endpoint de sugerencias"""

    suggestion: str = Field(..., description="Texto sugerido para continuar")
    model_used: str = Field(..., description="Modelo de IA utilizado")

    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "examples": [
                {
                    "suggestion": "existe una correlación significativa entre el uso de herramientas digitales y el rendimiento académico.",
                    "model_used": "gemini-2.0-flash-lite",
                }
            ]
        },
    }


# =============================================================================
# SCHEMAS PARA CITAS
# =============================================================================


class CitationAuthor(BaseModel):
    """Autor de una fuente bibliográfica"""

    apellido: str = Field(..., description="Apellido del autor")
    nombre: str | None = Field(
        None, description="Nombre(s) del autor (inicial o completo)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"apellido": "García", "nombre": "M."},
                {"apellido": "Smith", "nombre": "John"},
            ]
        }
    }


class CitationRequest(BaseModel):
    """Request para el endpoint de formateo de citas"""

    tipo: str = Field(
        ...,
        description="Tipo de fuente: 'libro', 'articulo', 'capitulo', 'tesis', 'web'",
    )
    autores: list[CitationAuthor] = Field(
        ..., description="Lista de autores de la fuente"
    )
    anio: int = Field(..., description="Año de publicación")
    titulo: str = Field(..., description="Título de la obra")

    # Campos específicos según tipo
    editorial: str | None = Field(None, description="Editorial (para libros)")
    revista: str | None = Field(
        None, description="Nombre de la revista (para artículos)"
    )
    volumen: int | None = Field(None, description="Volumen de la revista")
    numero: int | None = Field(None, description="Número de la revista")
    paginas: str | None = Field(None, description="Rango de páginas (ej: '123-145')")
    doi: str | None = Field(None, description="DOI de la publicación")
    url: str | None = Field(None, description="URL de acceso")
    editor: str | None = Field(None, description="Editor del libro (para capítulos)")
    titulo_libro: str | None = Field(
        None, description="Título del libro (para capítulos)"
    )
    institucion: str | None = Field(None, description="Institución (para tesis)")

    # Contexto del proyecto para mejorar la citación
    project_bibliography: list[BibliographyReference] = Field(
        default_factory=list,
        description="Bibliografía existente en el proyecto para verificar consistencia",
    )
    project_info: dict[str, Any] | None = Field(
        None,
        description="Información del proyecto (nombre, tipo de investigación, etc.)",
    )

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: str) -> str:
        tipos_validos = ["libro", "articulo", "capitulo", "tesis", "web"]
        if v.lower() not in tipos_validos:
            raise ValueError(f"El tipo debe ser uno de: {', '.join(tipos_validos)}")
        return v.lower()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tipo": "articulo",
                    "autores": [
                        {"apellido": "Smith", "nombre": "J."},
                        {"apellido": "Pérez", "nombre": "L."},
                    ],
                    "anio": 2019,
                    "titulo": "Innovación educativa en el siglo XXI",
                    "revista": "Revista de Educación",
                    "volumen": 45,
                    "numero": 2,
                    "paginas": "123-145",
                    "doi": "10.1234/re.2019.45.2.123",
                    "project_bibliography": [
                        {
                            "autores": "García, M.",
                            "anio": 2020,
                            "titulo": "Metodología educativa",
                            "tipo": "libro",
                        }
                    ],
                    "project_info": {
                        "name": "Investigación sobre innovación educativa",
                        "research_type": "cualitativa",
                    },
                }
            ]
        }
    }


class CitationResponse(BaseModel):
    """Response del endpoint de citas"""

    citation: str = Field(..., description="Cita formateada en estilo APA 7")
    model_used: str = Field(..., description="Modelo de IA utilizado")

    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "examples": [
                {
                    "citation": "Smith, J., & Pérez, L. (2019). Innovación educativa en el siglo XXI. *Revista de Educación*, 45(2), 123-145. https://doi.org/10.1234/re.2019.45.2.123",
                    "model_used": "gemini-2.0-flash-exp",
                }
            ]
        },
    }


# =============================================================================
# SCHEMAS PARA BIBLIOGRAFÍA
# =============================================================================


class BibliographyRequest(BaseModel):
    """Request para el endpoint de búsqueda de bibliografía"""

    query: str = Field(
        ...,
        description="Consulta de búsqueda para encontrar fuentes relevantes",
        min_length=3,
        max_length=500,
    )
    max_results: int = Field(
        10, description="Número máximo de resultados a devolver", ge=1, le=20
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "inteligencia artificial en educación superior",
                    "max_results": 10,
                }
            ]
        }
    }


class BibliographySource(BaseModel):
    """Una fuente bibliográfica encontrada"""

    titulo: str = Field(..., description="Título de la fuente")
    autores: list[str] = Field(..., description="Lista de autores")
    anio: int | None = Field(None, description="Año de publicación")
    tipo: str = Field(..., description="Tipo de fuente (articulo, libro, tesis, etc.)")
    fuente: str = Field(..., description="Nombre de la revista/editorial/institución")
    doi: str | None = Field(None, description="DOI si está disponible")
    url: str = Field(..., description="URL de acceso a la fuente")
    resumen: str = Field(..., description="Breve descripción de la relevancia")
    relevancia: int = Field(..., description="Score de relevancia (1-5)", ge=1, le=5)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "titulo": "Artificial Intelligence in Higher Education",
                    "autores": ["García, M.", "López, A."],
                    "anio": 2023,
                    "tipo": "articulo",
                    "fuente": "Journal of Educational Technology",
                    "doi": "10.1234/jet.2023.15.3.456",
                    "url": "https://example.com/article",
                    "resumen": "Estudio exhaustivo sobre implementación de IA en universidades",
                    "relevancia": 5,
                }
            ]
        }
    }


class BibliographyResponse(BaseModel):
    """Response del endpoint de bibliografía"""

    sources: list[BibliographySource] = Field(
        ..., description="Lista de fuentes encontradas, ordenadas por relevancia"
    )
    model_used: str = Field(..., description="Modelo de IA utilizado")
    total_found: int = Field(..., description="Número total de fuentes encontradas")

    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "examples": [
                {
                    "sources": [],  # Usar ejemplo de BibliographySource
                    "model_used": "gemini-2.0-flash-thinking-exp",
                    "total_found": 10,
                }
            ]
        },
    }


# =============================================================================
# SCHEMAS PARA ERRORES
# =============================================================================


class AIErrorResponse(BaseModel):
    """Response estándar para errores de IA"""

    error: str = Field(..., description="Tipo de error")
    message: str = Field(..., description="Mensaje de error descriptivo")
    details: dict[str, Any] | None = Field(
        None, description="Detalles adicionales del error"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "model_error",
                    "message": "El modelo de IA no respondió correctamente",
                    "details": {"status_code": 500},
                }
            ]
        }
    }
