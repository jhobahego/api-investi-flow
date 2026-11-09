import logging
from typing import Any

from app.core.celery_app import celery_app
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)


@celery_app.task(
    name="rag.index_attachment",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def index_attachment_task(self: Any, attachment_id: int) -> int:
    """Index one attachment's chunks. Exceptions propagate so Celery retries."""
    logger.info("Indexado RAG iniciado para adjunto %s", attachment_id)
    chunk_count = rag_service.index_attachment_in_session(attachment_id)
    logger.info(
        "Indexado RAG finalizado para adjunto %s (%s fragmentos)",
        attachment_id,
        chunk_count,
    )
    return chunk_count
