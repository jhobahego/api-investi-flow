"""Tests for LoggingMiddleware X-Request-ID propagation (TODO.md gaps).

Uses a minimal FastAPI app mounting only LoggingMiddleware, keeping tests
fast and isolated from the database and the full application.
"""

import logging
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.logging_middleware import LoggingMiddleware


def _build_client():
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/ping")
    def ping():
        return {"pong": True}

    return TestClient(app)


def test_request_id_passthrough_when_provided():
    client = _build_client()
    response = client.get("/ping", headers={"X-Request-ID": "req-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-123"


def test_request_id_generated_when_absent():
    client = _build_client()
    response = client.get("/ping")
    assert response.status_code == 200
    generated = response.headers["X-Request-ID"]
    assert generated
    # Must be a valid UUID produced by the middleware fallback.
    assert str(uuid.UUID(generated)) == generated


def test_response_header_echoes_request_id():
    client = _build_client()
    first = client.get("/ping")
    second = client.get("/ping")
    assert first.headers["X-Request-ID"]
    assert second.headers["X-Request-ID"]
    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]


def test_start_and_end_logs_emitted(caplog):
    client = _build_client()
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/ping", headers={"X-Request-ID": "req-log"})
    assert response.status_code == 200
    messages = [
        record.getMessage() for record in caplog.records if record.name == "app.request"
    ]
    assert any("Iniciando request" in message for message in messages)
    assert any("Request completado" in message for message in messages)
