"""Gemini cost guard (Phase 1): in-app rate limiting with free Upstash Redis.

Layers (cheap -> expensive, to avoid spending the global budget on rejected requests):
  0. Local per-IP in-memory prefilter (60/min, 0 Redis commands).
  1. Per-IP/min in Redis (moving window, 20/min).
  2. Per-user + feature/min in Redis (moving window).
  3. Per-user + feature/day count from PLAN_LIMITS (fixed window;
     -1 = unlimited, 0 = blocked with 403).
  4. Per-user daily token budget (fixed window, cost = worst case).
  5. Bibliography sub-cap (fixed window, 300k/day/user).
  6. Global daily token ceiling (fixed window, 503 with Retry-After).

Notes:
  - RATE_LIMIT_REDIS_URL and the Celery broker are independent: this
    guard only uses RATE_LIMIT_REDIS_URL (Upstash `async+rediss://` in prod,
    `async+redis://` locally). Celery is not used in prod.
  - Without Redis (invalid URL or down server) limiting continues with
    in-memory fallback + "Redis unavailable" log.
  - RATE_LIMIT_ENABLED=false = total bypass (tests only).
  - Server-side context truncation lives in `app/services/ai_service.py`
    (single place, protects all callers): chat <=12000 chars,
    suggestions doc <=12000, bibliography contexts <=6000.
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
except ImportError:  # pragma: no cover - only without the dep installed
    _LIMITS_AVAILABLE = False


# ----------------------------------------------------------------- constants

# Local prefilter: obvious floods without spending Redis commands.
LOCAL_IP_PREFILTER_PER_MIN = 60
# Shared IP/min (several people may share one IP).
IP_PER_MIN = 20
# User + feature/min (what a human actually uses).
USER_PER_MIN: dict[AIFeature, int] = {
    AIFeature.CHAT: 5,
    AIFeature.SUGGESTIONS: 10,
    AIFeature.CITATIONS: 10,
    AIFeature.BIBLIOGRAPHY: 3,
}

# 413: per-feature user prompt (full context is truncated separately).
PROMPT_MAX_CHARS: dict[AIFeature, int] = {
    AIFeature.CHAT: 5000,
    AIFeature.SUGGESTIONS: 12000,
    AIFeature.CITATIONS: 8000,
    AIFeature.BIBLIOGRAPHY: 6000,
}

# Server-side truncation caps (applied in ai_service, single place).
CHAT_CONTEXT_MAX_CHARS = 12000
SUGGESTION_DOC_MAX_CHARS = 12000
BIBLIOGRAPHY_CONTEXT_MAX_CHARS = 6000

_DEFAULT_GLOBAL_TOKENS_DAY = 1000000


# ------------------------------------------------------------ storage
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
            logger.exception("Redis unavailable, using in-memory limits")
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
else:  # pragma: no cover - only without the dep installed
    RateLimitItem = object  # type: ignore[assignment,misc]
    LOCAL_IP_PREFILTER = None
    IP_LIMIT = None
    _REDIS = {}
    _MEM = {}
    _LOCAL = None


# ----------------------------------------------------------------- helpers
def estimate_tokens(text: str) -> int:
    """Conservative estimate (~3 characters per token)."""
    return max(1, len(text) // 3)


def client_ip(http_request: Request) -> str:
    """Real IP via request.client.host (uvicorn --proxy-headers)."""
    if http_request.client is None:
        return "unknown"
    return http_request.client.host


def truncate_context(text: str | None, max_chars: int) -> str | None:
    """Server-side truncation of context before calling Gemini."""
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
    """One hit against Redis with in-memory fallback if Redis fails."""
    if kind == "local":
        return await _LOCAL.hit(item, *ids, cost=cost)  # type: ignore[union-attr]
    try:
        return await _REDIS[kind].hit(item, *ids, cost=cost)  # type: ignore[union-attr]
    except Exception:
        logger.exception("Redis unavailable, using in-memory limits")
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
    """Enforce Phase 1 limits before calling Gemini.

    Args:
        http_request: FastAPI Request (for the real IP).
        user_id: Stable user identifier.
        feature: AI feature (chat, suggestions, citations, bibliography).
        plan: User plan (estudiante, investigador, profesional).
        prompt_text: User message/query/text (cheap pre-check).

    Raises:
        HTTPException: 413 if the prompt exceeds the cap, 403 if the plan
            has no access, 429 if a limit is exceeded, 503 if the global
            ceiling is exhausted.
    """
    if not _rate_limit_enabled():
        return
    if not _LIMITS_AVAILABLE:
        logger.warning("limits not installed, rate limiting disabled")
        return

    feat = _normalize_feature(feature)
    user_plan = _normalize_plan(plan)

    max_chars = PROMPT_MAX_CHARS[feat]
    if len(prompt_text) > max_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Prompt exceeds {max_chars} characters",
        )

    ip = client_ip(http_request)
    cost = estimate_tokens(prompt_text) + _max_output_tokens(feat)

    # Cheap -> expensive order: global goes last to avoid spending budget
    # on requests that were already rejected.
    if not await _hit("local", LOCAL_IP_PREFILTER, ("ip-local", ip), 1):
        retry = await _retry_after("local", LOCAL_IP_PREFILTER, ("ip-local", ip))
        raise _deny(429, "Too many requests", retry)

    if not await _hit("moving", IP_LIMIT, ("ip", ip), 1):
        retry = await _retry_after("moving", IP_LIMIT, ("ip", ip))
        raise _deny(429, "Too many requests from your IP", retry)

    user_min = parse(f"{USER_PER_MIN[feat]}/minute")
    user_min_ids = ("user-min", user_id, feat.value)
    if not await _hit("moving", user_min, user_min_ids, 1):
        retry = await _retry_after("moving", user_min, user_min_ids)
        raise _deny(429, "Too many requests, please wait a moment", retry)

    daily_count = get_usage_limit(user_plan, feat)
    if daily_count == 0:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Feature '{feat.value}' is not available "
                f"on your current plan. Upgrade your plan to use it."
            ),
        )
    if daily_count > 0:
        count_limit = parse(f"{daily_count}/day")
        count_ids = ("user-feature-count", user_id, feat.value)
        if not await _hit("fixed", count_limit, count_ids, 1):
            retry = await _retry_after("fixed", count_limit, count_ids)
            raise _deny(429, "You reached your daily usage limit", retry)

    user_budget = USER_TOKENS_PER_DAY[user_plan]
    user_tokens = parse(f"{user_budget}/day")
    user_token_ids = ("user-tokens", user_id)
    if not await _hit("fixed", user_tokens, user_token_ids, cost):
        retry = await _retry_after("fixed", user_tokens, user_token_ids)
        raise _deny(429, "You reached your daily token quota", retry)

    if feat == AIFeature.BIBLIOGRAPHY:
        subcap = parse(f"{BIBLIOGRAPHY_TOKENS_PER_DAY_PER_USER}/day")
        subcap_ids = ("user-biblio-tokens", user_id)
        if not await _hit("fixed", subcap, subcap_ids, cost):
            retry = await _retry_after("fixed", subcap, subcap_ids)
            raise _deny(429, "You reached your daily bibliography quota", retry)

    global_limit = parse(f"{_global_tokens_day()}/day")
    global_ids = ("global-tokens",)
    if not await _hit("fixed", global_limit, global_ids, cost):
        retry = await _retry_after("fixed", global_limit, global_ids)
        raise _deny(503, "Service temporarily saturated", retry)
