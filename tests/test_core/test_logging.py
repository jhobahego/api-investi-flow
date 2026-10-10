"""Dedicated unit tests for app.core.logging (TODO.md logging gaps).

No network. No database. Deterministic formatter/filter assertions plus the
container-stdout contract for setup_logging.
"""

import json
import logging
import sys

import pytest

from app.core.logging import (
    ConsoleFormatter,
    ContextFilter,
    JsonFormatter,
    request_id_var,
    setup_logging,
    user_id_var,
)


def _make_record(msg="hello", name="test.logger", level=logging.INFO, **kwargs):
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname=__file__,
        lineno=10,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for key, value in kwargs.items():
        setattr(record, key, value)
    return record


@pytest.fixture
def clean_context():
    """Reset request/user contextvars before and after each test."""
    token_request = request_id_var.set(None)
    token_user = user_id_var.set(None)
    yield
    request_id_var.reset(token_request)
    user_id_var.reset(token_user)


@pytest.fixture
def restore_root_handlers():
    """Preserve root logger handlers across setup_logging tests."""
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    yield
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    for handler in saved_handlers:
        root.addHandler(handler)
    root.setLevel(saved_level)


def test_json_formatter_fields(clean_context):
    record = _make_record(request_id="req-1", user_id="user-1")
    data = json.loads(JsonFormatter().format(record))
    assert data["level"] == "INFO"
    assert data["logger"] == "test.logger"
    assert data["message"] == "hello"
    assert data["request_id"] == "req-1"
    assert data["user_id"] == "user-1"
    assert "timestamp" in data


def test_json_formatter_exception_key(clean_context):
    try:
        raise ValueError("boom")
    except ValueError:
        record = _make_record(request_id="req-1", user_id="user-1")
        record.exc_info = sys.exc_info()
    data = json.loads(JsonFormatter().format(record))
    assert "exception" in data
    assert "ValueError: boom" in data["exception"]


def test_console_formatter_contains_ids(clean_context):
    record = _make_record(request_id="req-9", user_id="user-9")
    output = ConsoleFormatter().format(record)
    assert "req-9" in output
    assert "user-9" in output
    assert "hello" in output


def test_context_filter_injects_defaults(clean_context):
    record = _make_record()
    assert ContextFilter().filter(record) is True
    assert record.request_id == "-"
    assert record.user_id == "-"


def test_context_filter_preserves_context_values(clean_context):
    token_request = request_id_var.set("req-ctx")
    token_user = user_id_var.set("user-ctx")
    try:
        record = _make_record()
        assert ContextFilter().filter(record) is True
        assert record.request_id == "req-ctx"
        assert record.user_id == "user-ctx"
    finally:
        request_id_var.reset(token_request)
        user_id_var.reset(token_user)


def test_setup_logging_uses_stdout(restore_root_handlers):
    setup_logging()
    root = logging.getLogger()
    assert len(root.handlers) == 1
    handler = root.handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    # Container contract: logs must go to stdout, not the stderr default.
    assert handler.stream is sys.stdout
    assert any(isinstance(f, ContextFilter) for f in handler.filters)
