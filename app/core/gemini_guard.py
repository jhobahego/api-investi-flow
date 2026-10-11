"""Gemini cost guard (Fase 1): rate limit en app con Upstash Redis free.

Capas (barato -> caro, para no gastar el presupuesto global en rechazados):
  0. Prefiltro local por IP en memoria (60/min, 0 comandos Redis).
  1. IP/min en Redis (moving window, 20/min).
  2. Usuario + feature/min en Redis (moving window).
  3. Usuario + feature/dia en count desde PLAN_LIMITS (fixed window;
     -1 = ilimitado, 0 = bloqueado con 403).
  4. Bolsa de tokens/dia por usuario (fixed window, costo = peor caso).
  5. Sub-techo de bibliography (fixed window, 300k/dia/usuario).
  6. Techo global de tokens/dia (fixed window, 503 con Retry-After).

Notas:
  - RATE_LIMIT_REDIS_URL y el broker de Celery son independientes: este
    guard solo usa RATE_LIMIT_REDIS_URL (Upstash `async+rediss://` en prod,
    `async+redis://` local). Celery no se usa en prod.
  - Sin Redis (URL invalida o servidor caido) se sigue limitando con
    fallback en memoria + log "Redis no disponible".
  - RATE_LIMIT_ENABLED=false = bypass total (solo tests).
  - El truncado server-side del contexto vive en `app/services/ai_service.py`
    (un solo lugar, protege a todos los callers): chat <=12000 chars,
    suggestions doc <=12000, bibliography contextos <=6000.
"""

import logging
import math
import os
import time

from fastapi import HTTPException, Request

from app.core.ai_config import (
    BIBLIOGRAPHY_TOKENS_PER_DAY_PER_USER,
    FEATURE_GENERATION_CONFIG,
    USER_TOKENS_PER_DAY,
    AIFeature,
    UserPlan,
    get_usage_limit,
)
from app.core.config import settings

logger = logging.getLogger("gemini-guard")

try:
    from limits import parse
    from limits.aio.storage import MemoryStorage
    from limits.aio.strategies import FixedWindowRateLimiter, MovingWindowRateLimiter
    from limits.storage import storage_from_string

    _LIMITS_AVAILABLE = True
except ImportError:  # pragma: no cover - solo sin instalar la dep
    _LIMITS_AVAILABLE = False


# ---------------------------------------------------------------- constantes

# Prefiltro local: floods obvios sin gastar comandos de Redis.
LOCAL_IP_PREFILTER_PER_MIN = 60
# IP/min compartido (varias personas pueden compartir IP).
IP_PER_MIN = 20
# Usuario + feature/min (lo que un humano usa de verdad).
USER_PER_MIN: dict[AIFeature, int] = {
    AIFeature.CHAT: 5,
    AIFeature.SUGGESTIONS: 10,
    AIFeature.CITATIONS: 10,
    AIFeature.BIBLIOGRAPHY: 3,
}

# 413: prompt del usuario por feature (el contexto completo va truncado aparte).
PROMPT_MAX_CHARS: dict[AIFeature, int] = {
    AIFeature.CHAT: 5000,
    AIFeature.SUGGESTIONS: 12000,
    AIFeature.CITATIONS: 8000,
    AIFeature.BIBLIOGRAPHY: 6000,
}

# Techos de truncado server-side (aplicados en ai_service, un solo lugar).
CHAT_CONTEXT_MAX_CHARS = 12000
SUGGESTION_DOC_MAX_CHARS = 12000
BIBLIOGRAPHY_CONTEXT_MAX_CHARS = 6000

_DEFAULT_GLOBAL_TOKENS_DAY = 1000000


# ------------------------------------------------------- almacenamiento
if _LIMITS_AVAILABLE:
    from limits import RateLimitItem  # noqa: E402

    LOCAL_IP_PREFILTER = parse(f"{LOCAL_IP_PREFILTER_PER_MIN}/minute")
    IP_LIMIT = parse(f"{IP_PER_MIN}/minute")

    def _build_redis_storage() -> object:
        url = (
            os.getenv("RATE_LIMIT_REDIS_URL")
            or settings.RATE_LIMIT_REDIS_URL
            or "async+redis://localhost:6379"
        )
        try:
            return storage_from_string(
                url,
                socket_connect_timeout=1,
                socket_timeout=1,
                max_connections=5,
            )
        except Exception:
            logger.exception("Redis no disponible, usando límites en memoria")
            return MemoryStorage()

    _redis_storage = _build_redis_storage()
    _memory_storage = MemoryStorage()

    _REDIS = {
        "moving": MovingWindowRateLimiter(_redis_storage),  # type: ignore[arg-type]
        "fixed": FixedWindowRateLimiter(_redis_storage),  # type: ignore[arg-type]
    }
    _MEM = {
        "moving": MovingWindowRateLimiter(_memory_storage),
        "fixed": FixedWindowRateLimiter(_memory_storage),
    }
    _LOCAL = MovingWindowRateLimiter(MemoryStorage())
else:  # pragma: no cover - solo sin instalar la dep
    RateLimitItem = object  # type: ignore[assignment,misc]
    LOCAL_IP_PREFILTER = None
    IP_LIMIT = None
    _REDIS = {}
    _MEM = {}
    _LOCAL = None


# ------------------------------------------------------------- utilidades
def estimate_tokens(text: str) -> int:
    """Estimacion conservadora (~3 caracteres por token)."""
    return max(1, len(text) // 3)


def client_ip(http_request: Request) -> str:
    """IP real via request.client.host (uvicorn --proxy-headers)."""
    if http_request.client is None:
        return "unknown"
    return http_request.client.host


def truncate_context(text: str | None, max_chars: int) -> str | None:
    """Truncado server-side del contexto antes de llamar a Gemini."""
    if text is None:
        return None
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _rate_limit_enabled() -> bool:
    raw = os.getenv("RATE_LIMIT_ENABLED")
    if raw is not None:
        return raw.strip().lower() not in ("false", "0", "no", "off")
    return bool(settings.RATE_LIMIT_ENABLED)


def _global_tokens_day() -> int:
    raw = os.getenv("GEMINI_GLOBAL_TOKENS_DAY")
    if raw is None:
        return int(settings.GEMINI_GLOBAL_TOKENS_DAY)
    try:
        return max(1, int(raw))
    except ValueError:
        return _DEFAULT_GLOBAL_TOKENS_DAY


def _normalize_feature(feature: AIFeature | str) -> AIFeature:
    if isinstance(feature, AIFeature):
        return feature
    return AIFeature(str(feature))


def _normalize_plan(plan: UserPlan | str) -> UserPlan:
    if isinstance(plan, UserPlan):
        return plan
    return UserPlan(str(plan))


def _max_output_tokens(feature: AIFeature) -> int:
    config = FEATURE_GENERATION_CONFIG.get(feature, {})
    value = config.get("max_output_tokens", 2048)
    return int(value)


async def _hit(kind: str, item: object, ids: tuple[str, ...], cost: int) -> bool:
    """Un hit contra Redis con fallback a memoria si Redis falla."""
    if kind == "local":
        return await _LOCAL.hit(item, *ids, cost=cost)  # type: ignore[union-attr]
    try:
        return await _REDIS[kind].hit(item, *ids, cost=cost)  # type: ignore[union-attr]
    except Exception:
        logger.exception("Redis no disponible, usando límites en memoria")
        return await _MEM[kind].hit(item, *ids, cost=cost)  # type: ignore[union-attr]


async def _retry_after(kind: str, item: object, ids: tuple[str, ...]) -> int:
    try:
        strategy = _LOCAL if kind == "local" else _REDIS[kind]
        stats = await strategy.get_window_stats(item, *ids)  # type: ignore[union-attr]
        return max(1, math.ceil(stats.reset_time - time.time()))
    except Exception:
        return 60


def _deny(status_code: int, message: str, retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=message,
        headers={"Retry-After": str(retry_after)},
    )


# ------------------------------------------------------------ enforcement
async def enforce_gemini_limits(
    http_request: Request,
    user_id: str,
    feature: AIFeature | str,
    plan: UserPlan | str,
    prompt_text: str,
) -> None:
    """Aplica los limites Fase 1 antes de llamar a Gemini.

    Args:
        http_request: Request de FastAPI (para la IP real).
        user_id: Identificador estable del usuario.
        feature: Feature de IA (chat, suggestions, citations, bibliography).
        plan: Plan del usuario (estudiante, investigador, profesional).
        prompt_text: Mensaje/query/texto del usuario (pre-check barato).

    Raises:
        HTTPException: 413 si el prompt supera el cap, 403 si el plan no
            tiene acceso, 429 si se excede un limite, 503 si el techo
            global se agoto.
    """
    if not _rate_limit_enabled():
        return
    if not _LIMITS_AVAILABLE:
        logger.warning("limits no instalado, sin rate limiting")
        return

    feat = _normalize_feature(feature)
    user_plan = _normalize_plan(plan)

    max_chars = PROMPT_MAX_CHARS[feat]
    if len(prompt_text) > max_chars:
        raise HTTPException(
            status_code=413,
            detail=f"El prompt supera {max_chars} caracteres",
        )

    ip = client_ip(http_request)
    cost = estimate_tokens(prompt_text) + _max_output_tokens(feat)

    # Orden barato -> caro: lo global va al final para no gastar presupuesto
    # en peticiones que ya fueron rechazadas.
    if not await _hit("local", LOCAL_IP_PREFILTER, ("ip-local", ip), 1):
        retry = await _retry_after("local", LOCAL_IP_PREFILTER, ("ip-local", ip))
        raise _deny(429, "Demasiadas peticiones", retry)

    if not await _hit("moving", IP_LIMIT, ("ip", ip), 1):
        retry = await _retry_after("moving", IP_LIMIT, ("ip", ip))
        raise _deny(429, "Demasiadas peticiones desde tu IP", retry)

    user_min = parse(f"{USER_PER_MIN[feat]}/minute")
    user_min_ids = ("user-min", user_id, feat.value)
    if not await _hit("moving", user_min, user_min_ids, 1):
        retry = await _retry_after("moving", user_min, user_min_ids)
        raise _deny(429, "Demasiadas peticiones, espera un momento", retry)

    daily_count = get_usage_limit(user_plan, feat)
    if daily_count == 0:
        raise HTTPException(
            status_code=403,
            detail=(
                f"La funcionalidad '{feat.value}' no esta disponible "
                f"en tu plan actual. Actualiza tu plan para usarla."
            ),
        )
    if daily_count > 0:
        count_limit = parse(f"{daily_count}/day")
        count_ids = ("user-feature-count", user_id, feat.value)
        if not await _hit("fixed", count_limit, count_ids, 1):
            retry = await _retry_after("fixed", count_limit, count_ids)
            raise _deny(429, "Alcanzaste tu limite diario de usos", retry)

    user_budget = USER_TOKENS_PER_DAY[user_plan]
    user_tokens = parse(f"{user_budget}/day")
    user_token_ids = ("user-tokens", user_id)
    if not await _hit("fixed", user_tokens, user_token_ids, cost):
        retry = await _retry_after("fixed", user_tokens, user_token_ids)
        raise _deny(429, "Alcanzaste tu cuota diaria de tokens", retry)

    if feat == AIFeature.BIBLIOGRAPHY:
        subcap = parse(f"{BIBLIOGRAPHY_TOKENS_PER_DAY_PER_USER}/day")
        subcap_ids = ("user-biblio-tokens", user_id)
        if not await _hit("fixed", subcap, subcap_ids, cost):
            retry = await _retry_after("fixed", subcap, subcap_ids)
            raise _deny(429, "Alcanzaste tu cuota diaria de bibliografia", retry)

    global_limit = parse(f"{_global_tokens_day()}/day")
    global_ids = ("global-tokens",)
    if not await _hit("fixed", global_limit, global_ids, cost):
        retry = await _retry_after("fixed", global_limit, global_ids)
        raise _deny(503, "Servicio temporalmente saturado", retry)
