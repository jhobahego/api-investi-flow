"""Celery queue wiring: the API publishes to the configured queue."""

from app.core.celery_app import celery_app
from app.core.config import settings


def test_task_default_queue_matches_settings() -> None:
    assert celery_app.conf.task_default_queue == settings.CELERY_QUEUE_NAME
