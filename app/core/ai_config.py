from enum import Enum


class UserPlan(str, Enum):
    """Planes de usuario disponibles en la plataforma"""

    ESTUDIANTE = "estudiante"  # Plan gratuito
    INVESTIGADOR = "investigador"  # Plan Pro
    PROFESIONAL = "profesional"  # Plan Avanzado


class AIFeature(str, Enum):
    """Funcionalidades de IA disponibles"""

    CHAT = "chat"
    SUGGESTIONS = "suggestions"
    CITATIONS = "citations"
    BIBLIOGRAPHY = "bibliography"


# =============================================================================
# CONFIGURACIÓN DE MODELOS POR PLAN
# =============================================================================

PLAN_MODELS: dict[UserPlan, dict[AIFeature, str | None]] = {
    UserPlan.ESTUDIANTE: {
        AIFeature.CHAT: "gemini-2.0-flash-exp",  # Modelo rápido para chat básico
        AIFeature.SUGGESTIONS: "gemini-2.0-flash-lite-001",  # Modelo ultraligero para sugerencias
        AIFeature.CITATIONS: "gemini-2.0-flash-exp",  # Flash para formateo de citas
        AIFeature.BIBLIOGRAPHY: None,  # No disponible en plan gratuito
    },
    UserPlan.INVESTIGADOR: {
        AIFeature.CHAT: "gemini-2.0-flash-exp",  # Flash para conversaciones
        AIFeature.SUGGESTIONS: "gemini-2.0-flash-lite-001",  # Lite para autocompletado rápido
        AIFeature.CITATIONS: "gemini-2.0-flash-exp",  # Flash para citas
        AIFeature.BIBLIOGRAPHY: "gemini-2.0-flash-exp",  # Flash con Grounding para búsqueda
    },
    UserPlan.PROFESIONAL: {
        AIFeature.CHAT: "gemini-2.0-flash-lite-001",  # Thinking para análisis profundo
        AIFeature.SUGGESTIONS: "gemini-2.0-flash-exp",  # Flash para sugerencias rápidas
        AIFeature.CITATIONS: "gemini-2.0-flash-exp",  # Flash para formateo preciso
        AIFeature.BIBLIOGRAPHY: "gemini-2.0-flash-lite-001",  # Thinking con Grounding
    },
}


# =============================================================================
# CARACTERÍSTICAS DISPONIBLES POR PLAN
# =============================================================================

PLAN_FEATURES: dict[UserPlan, dict[AIFeature, bool]] = {
    UserPlan.ESTUDIANTE: {
        AIFeature.CHAT: True,
        AIFeature.SUGGESTIONS: True,
        AIFeature.CITATIONS: True,
        AIFeature.BIBLIOGRAPHY: False,  # Restringido
    },
    UserPlan.INVESTIGADOR: {
        AIFeature.CHAT: True,
        AIFeature.SUGGESTIONS: True,
        AIFeature.CITATIONS: True,
        AIFeature.BIBLIOGRAPHY: True,
    },
    UserPlan.PROFESIONAL: {
        AIFeature.CHAT: True,
        AIFeature.SUGGESTIONS: True,
        AIFeature.CITATIONS: True,
        AIFeature.BIBLIOGRAPHY: True,
    },
}


# =============================================================================
# LÍMITES DE USO POR PLAN (para implementación futura)
# =============================================================================

PLAN_LIMITS: dict[UserPlan, dict[str, int]] = {
    UserPlan.ESTUDIANTE: {
        "chat_messages_per_day": 50,
        "suggestions_per_day": 100,
        "citations_per_day": 20,
        "bibliography_searches_per_day": 0,  # No disponible
    },
    UserPlan.INVESTIGADOR: {
        "chat_messages_per_day": 200,
        "suggestions_per_day": 500,
        "citations_per_day": 100,
        "bibliography_searches_per_day": 50,
    },
    UserPlan.PROFESIONAL: {
        "chat_messages_per_day": -1,  # Ilimitado
        "suggestions_per_day": -1,  # Ilimitado
        "citations_per_day": -1,  # Ilimitado
        "bibliography_searches_per_day": -1,  # Ilimitado
    },
}


# =============================================================================
# CONFIGURACIÓN GENERAL DE MODELOS
# =============================================================================

MODEL_GENERATION_CONFIG: dict[str, dict[str, float | int]] = {
    "gemini-2.0-flash-lite": {
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 1024,
    },
    "gemini-2.0-flash-exp": {
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 2048,
    },
    "gemini-2.0-flash-lite-001": {
        "temperature": 0.8,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
    },
}

# Configuraciones específicas por funcionalidad (overrides opcionales)
FEATURE_GENERATION_CONFIG: dict[AIFeature, dict[str, float | int]] = {
    AIFeature.CHAT: {
        "temperature": 0.8,  # Mayor creatividad en conversación
        "max_output_tokens": 4096,
    },
    AIFeature.SUGGESTIONS: {
        "temperature": 0.7,  # Balance creatividad/coherencia
        "max_output_tokens": 512,  # Sugerencias cortas
    },
    AIFeature.CITATIONS: {
        "temperature": 0.2,  # Baja temperatura para precisión en formateo
        "max_output_tokens": 1024,
    },
    AIFeature.BIBLIOGRAPHY: {
        "temperature": 0.5,  # Moderada para búsqueda estructurada
        "max_output_tokens": 4096,  # Múltiples fuentes
    },
}


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================


def get_model_for_feature(
    feature: AIFeature, plan: UserPlan = UserPlan.PROFESIONAL
) -> str | None:
    """
    Obtiene el modelo de IA apropiado para una funcionalidad y plan específico.

    Args:
        feature: La funcionalidad de IA solicitada
        plan: El plan del usuario (por defecto: PROFESIONAL para desarrollo)

    Returns:
        str | None: El nombre del modelo de Gemini a usar, o None si no está disponible

    Raises:
        ValueError: Si la funcionalidad no está disponible para el plan
    """
    if not is_feature_available(feature, plan):
        raise ValueError(
            f"La funcionalidad '{feature.value}' no está disponible "
            f"para el plan '{plan.value}'"
        )

    return PLAN_MODELS[plan][feature]


def is_feature_available(feature: AIFeature, plan: UserPlan) -> bool:
    """
    Verifica si una funcionalidad está disponible para un plan específico.

    Args:
        feature: La funcionalidad de IA a verificar
        plan: El plan del usuario

    Returns:
        bool: True si la funcionalidad está disponible, False si no
    """
    return PLAN_FEATURES[plan].get(feature, False)


def get_generation_config(model_name: str, feature: AIFeature | None = None) -> dict:
    """
    Obtiene la configuración de generación para un modelo específico.

    Args:
        model_name: Nombre del modelo de Gemini
        feature: Funcionalidad de IA (opcional) para aplicar overrides específicos

    Returns:
        dict: Configuración de generación del modelo
    """
    # Obtener configuración base del modelo
    config = MODEL_GENERATION_CONFIG.get(
        model_name,
        MODEL_GENERATION_CONFIG["gemini-2.0-flash-exp"],  # Default
    ).copy()

    # Aplicar overrides específicos de la funcionalidad si existe
    if feature and feature in FEATURE_GENERATION_CONFIG:
        feature_overrides = FEATURE_GENERATION_CONFIG[feature]
        config.update(feature_overrides)

    return config


def get_usage_limit(plan: UserPlan, feature: AIFeature) -> int:
    """
    Obtiene el límite de uso diario para una funcionalidad según el plan.

    Args:
        plan: El plan del usuario
        feature: La funcionalidad de IA

    Returns:
        int: Límite de uso (-1 significa ilimitado, 0 significa no disponible)
    """
    feature_key = f"{feature.value}_per_day"
    if feature == AIFeature.CHAT:
        feature_key = "chat_messages_per_day"
    elif feature == AIFeature.SUGGESTIONS:
        feature_key = "suggestions_per_day"
    elif feature == AIFeature.CITATIONS:
        feature_key = "citations_per_day"
    elif feature == AIFeature.BIBLIOGRAPHY:
        feature_key = "bibliography_searches_per_day"

    return PLAN_LIMITS[plan].get(feature_key, 0)
