import ssl

from celery import Celery  # type: ignore[import-untyped]

from app.core.config import settings

_broker = settings.CELERY_BROKER_URL or settings.REDIS_URL or "redis://localhost:6379/0"
_backend = (
    settings.CELERY_RESULT_BACKEND or settings.REDIS_URL or "redis://localhost:6379/0"
)

# Celery refuses `rediss://` URLs without an explicit certificate policy.
# Upstash (and most managed Redis) use TLS, so configure it from the scheme
# instead of requiring `?ssl_cert_reqs=required` in every URL.
_ssl_conf: dict[str, object] = {}
if _broker.startswith("rediss://"):
    _ssl_conf["broker_use_ssl"] = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
if _backend.startswith("rediss://"):
    _ssl_conf["redis_backend_use_ssl"] = {"ssl_cert_reqs": ssl.CERT_REQUIRED}

celery_app = Celery(
    "investi_flow",
    broker=_broker,
    backend=_backend,
    include=["app.tasks.rag_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="rag",
    **_ssl_conf,
)
