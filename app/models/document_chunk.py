"""Document chunks with vector embeddings (pgvector on PostgreSQL).

The embedding column uses a custom TypeDecorator so the same ORM model works
on PostgreSQL (native ``vector`` type via pgvector) and on SQLite (JSON text),
which is what the test suite runs on.
"""

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.database import Base

EMBEDDING_DIMENSION = 768


class EmbeddingType(TypeDecorator[Text]):
    """Embedding stored as pgvector ``Vector(768)`` or JSON text on SQLite."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(EMBEDDING_DIMENSION))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps([float(x) for x in value])

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return list(value)
        if isinstance(value, list):
            return value
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return None


class DocumentChunk(Base):
    """A text fragment of an attachment plus its embedding vector."""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    attachment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("attachments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[Any]] = mapped_column(EmbeddingType(), nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "attachment_id",
            "chunk_index",
            name="uq_document_chunks_attachment_chunk",
        ),
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
