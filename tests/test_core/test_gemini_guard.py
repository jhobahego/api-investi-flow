"""Tests for the Gemini cost guard (Phase 1).

The guard enforces per-IP, per-user and token-budget limits before any
Gemini call. These tests run against in-memory storage only and never
require a real Redis instance.
"""

import uuid

import pytest
from fastapi import HTTPException, Request

from app.core import gemini_guard as guard
from app.core.ai_config import UserPlan


def _make_request(ip: str = "127.0.0.1") -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "headers": [],
        "client": (ip, 50000),
        "path": "/api/v1/ia/sugerencias",
    }
    return Request(scope)


def _uid() -> str:
    return f"test-user-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def mem_guard(monkeypatch: pytest.MonkeyPatch) -> object:
    """Fresh in-memory limiters with the guard enabled."""
    from limits.aio.storage import MemoryStorage
    from limits.aio.strategies import FixedWindowRateLimiter, MovingWindowRateLimiter

    mem = MemoryStorage()
    monkeypatch.setattr(
        guard,
        "_REDIS",
        {
            "moving": MovingWindowRateLimiter(mem),
            "fixed": FixedWindowRateLimiter(mem),
        },
    )
    fallback = MemoryStorage()
    monkeypatch.setattr(
        guard,
        "_MEM",
        {
            "moving": MovingWindowRateLimiter(fallback),
            "fixed": FixedWindowRateLimiter(fallback),
        },
    )
    monkeypatch.setattr(guard, "_LOCAL", MovingWindowRateLimiter(MemoryStorage()))
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.delenv("GEMINI_GLOBAL_TOKENS_DAY", raising=False)
    monkeypatch.delenv("RATE_LIMIT_REDIS_URL", raising=False)
    return guard


def test_estimate_tokens_conservative() -> None:
    assert guard.estimate_tokens("") == 1
    assert guard.estimate_tokens("abc") == 1
    assert guard.estimate_tokens("abcdef") == 2
    assert guard.estimate_tokens("x" * 300) == 100


def test_truncate_context() -> None:
    assert guard.truncate_context(None, 100) is None
    assert guard.truncate_context("short", 100) == "short"
    long_text = "x" * 150
    assert guard.truncate_context(long_text, 100) == "x" * 100


def test_client_ip_uses_request_client_host() -> None:
    assert guard.client_ip(_make_request("9.9.9.9")) == "9.9.9.9"


@pytest.mark.asyncio
async def test_chat_user_per_min_429_with_retry_after(
    mem_guard: object,
) -> None:
    request = _make_request()
    user_id = _uid()
    for _ in range(5):
        await guard.enforce_gemini_limits(
            request,
            user_id=user_id,
            feature="chat",
            plan=UserPlan.PROFESIONAL,
            prompt_text="hello",
        )
    with pytest.raises(HTTPException) as exc_info:
        await guard.enforce_gemini_limits(
            request,
            user_id=user_id,
            feature="chat",
            plan=UserPlan.PROFESIONAL,
            prompt_text="hello",
        )
    assert exc_info.value.status_code == 429
    assert exc_info.value.headers is not None
    assert "Retry-After" in exc_info.value.headers


@pytest.mark.asyncio
async def test_prompt_over_cap_returns_413(mem_guard: object) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await guard.enforce_gemini_limits(
            _make_request(),
            user_id=_uid(),
            feature="chat",
            plan=UserPlan.PROFESIONAL,
            prompt_text="x" * 5001,
        )
    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
async def test_redis_failure_falls_back_to_memory(
    mem_guard: object, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class _BrokenLimiter:
        async def hit(self, *args: object, **kwargs: object) -> bool:
            raise ConnectionError("redis down")

        async def get_window_stats(self, *args: object, **kwargs: object) -> object:
            raise ConnectionError("redis down")

    monkeypatch.setattr(
        guard, "_REDIS", {"moving": _BrokenLimiter(), "fixed": _BrokenLimiter()}
    )
    request = _make_request()
    user_id = _uid()
    with caplog.at_level("WARNING", logger="gemini-guard"):
        for _ in range(5):
            await guard.enforce_gemini_limits(
                request,
                user_id=user_id,
                feature="chat",
                plan=UserPlan.PROFESIONAL,
                prompt_text="hello",
            )
    assert "Redis unavailable" in caplog.text
    with pytest.raises(HTTPException) as exc_info:
        await guard.enforce_gemini_limits(
            request,
            user_id=user_id,
            feature="chat",
            plan=UserPlan.PROFESIONAL,
            prompt_text="hello",
        )
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_estudiante_bibliography_blocked_403(
    mem_guard: object,
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await guard.enforce_gemini_limits(
            _make_request(),
            user_id=_uid(),
            feature="bibliography",
            plan=UserPlan.ESTUDIANTE,
            prompt_text="quantum computing",
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_global_ceiling_returns_503(
    mem_guard: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GEMINI_GLOBAL_TOKENS_DAY", "1")
    with pytest.raises(HTTPException) as exc_info:
        await guard.enforce_gemini_limits(
            _make_request(),
            user_id=_uid(),
            feature="chat",
            plan=UserPlan.PROFESIONAL,
            prompt_text="hello",
        )
    assert exc_info.value.status_code == 503
    assert exc_info.value.headers is not None
    assert "Retry-After" in exc_info.value.headers


@pytest.mark.asyncio
async def test_rate_limit_disabled_bypasses(
    mem_guard: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    for _ in range(10):
        await guard.enforce_gemini_limits(
            _make_request(),
            user_id=_uid(),
            feature="chat",
            plan=UserPlan.PROFESIONAL,
            prompt_text="hello",
        )
