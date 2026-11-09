"""Tests for the document RAG service (chunking, embeddings, retrieval)."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy import text as sa_text

from app.core.config import settings
from app.models.attachment import Attachment, FileType
from app.models.document_chunk import EMBEDDING_DIMENSION, DocumentChunk
from app.models.project import Project
from app.models.user import User
from app.services.rag_service import RAGServiceError, rag_service


def _make_attachment(db_session, **kwargs) -> Attachment:
    """Create and persist a minimal attachment for the given parent."""
    attachment = Attachment(
        file_name=kwargs.pop("file_name", "documento.docx"),
        file_path=kwargs.pop("file_path", "/tmp/documento.docx"),
        file_type=kwargs.pop("file_type", FileType.DOCX),
        file_size=kwargs.pop("file_size", 1024),
        **kwargs,
    )
    db_session.add(attachment)
    db_session.commit()
    db_session.refresh(attachment)
    return attachment


def _unit_vector(position: int) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSION
    vector[position] = 1.0
    return vector


# --------------------------------------------------------------------- chunking
def test_chunk_text_splits_long_text_with_overlap():
    paragraph = ("texto de investigación académica " * 15).strip()
    text = f"{paragraph}\n\n{paragraph}\n\n{paragraph}"

    chunks = rag_service.chunk_text(text, chunk_size=900, overlap=120)

    assert len(chunks) >= 2
    assert all(chunk.strip() for chunk in chunks)
    assert all(len(chunk) <= 900 for chunk in chunks)
    # The tail of one chunk is carried into the next one (sliding window).
    assert chunks[0][-40:] in chunks[1]


def test_chunk_text_splits_single_long_paragraph():
    long_paragraph = " ".join(f"palabra{index}" for index in range(500))

    chunks = rag_service.chunk_text(long_paragraph, chunk_size=900, overlap=120)

    assert len(chunks) >= 3
    assert all(chunk.strip() for chunk in chunks)
    assert all(len(chunk) <= 900 for chunk in chunks)
    assert all(len(chunk) >= 200 for chunk in chunks)


def test_chunk_text_returns_empty_for_blank_text():
    assert rag_service.chunk_text("") == []
    assert rag_service.chunk_text("   \n\n  ") == []


# -------------------------------------------------------------------- embedding
def test_embed_texts_returns_vectors(monkeypatch):
    client = MagicMock()
    response = MagicMock()
    first = MagicMock()
    first.values = [0.1] * EMBEDDING_DIMENSION
    second = MagicMock()
    second.values = [0.2] * EMBEDDING_DIMENSION
    response.embeddings = [first, second]
    client.models.embed_content.return_value = response
    monkeypatch.setattr(rag_service, "_client", client)

    vectors = rag_service.embed_texts(["texto uno", "texto dos"])

    assert len(vectors) == 2
    assert len(vectors[0]) == EMBEDDING_DIMENSION
    assert vectors[0][0] == pytest.approx(0.1)
    assert vectors[1][0] == pytest.approx(0.2)
    client.models.embed_content.assert_called_once()


def test_embed_texts_without_api_key_raises(monkeypatch):
    monkeypatch.setattr(rag_service, "_client", None)
    monkeypatch.setattr(settings, "GOOGLE_AI_API_KEY", None)

    with pytest.raises(RAGServiceError):
        rag_service.embed_texts(["texto"])


def test_embed_texts_rejects_wrong_dimension(monkeypatch):
    client = MagicMock()
    response = MagicMock()
    wrong = MagicMock()
    wrong.values = [0.1] * 10
    response.embeddings = [wrong]
    client.models.embed_content.return_value = response
    monkeypatch.setattr(rag_service, "_client", client)

    with pytest.raises(RAGServiceError):
        rag_service.embed_texts(["texto"])


# --------------------------------------------------------------------- indexing
def test_index_attachment_persists_chunks(db_session, test_project, monkeypatch):
    attachment = _make_attachment(db_session, project_id=test_project.id)
    text = ("contenido de prueba " * 250).strip()

    monkeypatch.setattr(rag_service, "extract_text", lambda _attachment: text)
    monkeypatch.setattr(
        rag_service,
        "embed_texts",
        lambda texts: [[0.1] * EMBEDDING_DIMENSION for _ in texts],
    )

    count = rag_service.index_attachment(db_session, attachment)

    assert count > 1
    rows = (
        db_session.query(DocumentChunk)
        .filter_by(attachment_id=attachment.id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )
    assert len(rows) == count
    assert [row.chunk_index for row in rows] == list(range(count))
    assert all(row.project_id == test_project.id for row in rows)
    assert all(isinstance(row.embedding, list) for row in rows)
    assert all(len(row.embedding) == EMBEDDING_DIMENSION for row in rows)
    assert all(row.token_count >= 1 for row in rows)

    raw_embedding = db_session.execute(
        sa_text("SELECT embedding FROM document_chunks WHERE id = :row_id"),
        {"row_id": rows[0].id},
    ).scalar()
    assert isinstance(raw_embedding, str)
    assert raw_embedding.lstrip().startswith("[")


def test_index_attachment_replaces_old_chunks(db_session, test_project, monkeypatch):
    attachment = _make_attachment(db_session, project_id=test_project.id)
    old_text = ("contenido viejo " * 250).strip()
    new_text = ("contenido nuevo " * 250).strip()

    monkeypatch.setattr(rag_service, "extract_text", lambda _attachment: old_text)
    monkeypatch.setattr(
        rag_service,
        "embed_texts",
        lambda texts: [[0.1] * EMBEDDING_DIMENSION for _ in texts],
    )
    old_count = rag_service.index_attachment(db_session, attachment)

    monkeypatch.setattr(rag_service, "extract_text", lambda _attachment: new_text)
    new_count = rag_service.index_attachment(db_session, attachment)

    rows = db_session.query(DocumentChunk).filter_by(attachment_id=attachment.id).all()
    assert new_count == old_count == len(rows)
    # SQLite may reuse deleted rowids, so identity by id is not asserted;
    # the replacement is verified by content. Later chunks may start mid-word
    # because of the overlap window, so content is checked with ``in``.
    assert all("contenido nuevo" in row.content for row in rows)
    assert all("contenido viejo" not in row.content for row in rows)


def test_index_attachment_without_project_raises(db_session, monkeypatch):
    attachment = Attachment(
        file_name="suelto.docx",
        file_path="/tmp/suelto.docx",
        file_type=FileType.DOCX,
        file_size=1024,
    )
    monkeypatch.setattr(rag_service, "extract_text", lambda _attachment: "texto")

    with pytest.raises(ValueError):
        rag_service.index_attachment(db_session, attachment)


def test_index_attachment_without_chunks_clears_existing(
    db_session, test_project, monkeypatch
):
    attachment = _make_attachment(db_session, project_id=test_project.id)
    db_session.add(
        DocumentChunk(
            attachment_id=attachment.id,
            project_id=test_project.id,
            chunk_index=0,
            content="viejo",
            embedding=[0.1] * EMBEDDING_DIMENSION,
            token_count=1,
        )
    )
    db_session.commit()

    monkeypatch.setattr(rag_service, "extract_text", lambda _attachment: "   ")

    count = rag_service.index_attachment(db_session, attachment)

    assert count == 0
    assert (
        db_session.query(DocumentChunk).filter_by(attachment_id=attachment.id).count()
        == 0
    )


def test_enqueue_skipped_when_disabled(monkeypatch):
    monkeypatch.setenv("RAG_INDEXING_ENABLED", "false")

    from app.tasks import rag_tasks

    def _fail(_attachment_id: int) -> None:
        raise AssertionError("index_attachment_task.delay must not be called")

    monkeypatch.setattr(rag_tasks.index_attachment_task, "delay", _fail)

    assert rag_service.enqueue_attachment_indexing(1) is False


def test_index_attachment_in_session(db_session, test_project, monkeypatch):
    attachment = _make_attachment(db_session, project_id=test_project.id)
    monkeypatch.setattr("app.services.rag_service.SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(
        rag_service, "extract_text", lambda _attachment: "contenido de prueba " * 300
    )
    monkeypatch.setattr(
        rag_service,
        "embed_texts",
        lambda texts: [[0.1] * EMBEDDING_DIMENSION for _ in texts],
    )

    count = rag_service.index_attachment_in_session(attachment.id)

    assert count > 0
    rows = db_session.query(DocumentChunk).filter_by(attachment_id=attachment.id).all()
    assert len(rows) == count


# -------------------------------------------------------------------- retrieval
def test_retrieve_for_attachment_scopes_and_orders(
    db_session, test_user, test_project, monkeypatch
):
    other_user = User(
        email="other@example.com",
        full_name="Other User",
        hashed_password="hashed",
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    other_project = Project(
        name="Other Project",
        description="Other",
        status="planning",
        owner_id=other_user.id,
    )
    db_session.add(other_project)
    db_session.commit()
    db_session.refresh(other_project)

    attachment = _make_attachment(
        db_session, file_name="propio.docx", project_id=test_project.id
    )
    foreign_attachment = _make_attachment(
        db_session, file_name="ajeno.docx", project_id=other_project.id
    )

    db_session.add_all(
        [
            DocumentChunk(
                attachment_id=attachment.id,
                project_id=test_project.id,
                chunk_index=0,
                content="alpha",
                embedding=_unit_vector(0),
                token_count=1,
            ),
            DocumentChunk(
                attachment_id=attachment.id,
                project_id=test_project.id,
                chunk_index=1,
                content="beta",
                embedding=_unit_vector(1),
                token_count=1,
            ),
            DocumentChunk(
                attachment_id=foreign_attachment.id,
                project_id=other_project.id,
                chunk_index=0,
                content="gamma",
                embedding=_unit_vector(0),
                token_count=1,
            ),
        ]
    )
    db_session.commit()

    monkeypatch.setattr(rag_service, "embed_texts", lambda _texts: [_unit_vector(0)])

    results = rag_service.retrieve_for_attachment(
        db_session,
        attachment_id=attachment.id,
        user_id=test_user.id,
        query="consulta",
        top_k=5,
    )

    assert len(results) == 2
    assert all(result["attachment_id"] == attachment.id for result in results)
    assert not any(result["content"] == "gamma" for result in results)
    assert results[0]["chunk_index"] == 0
    assert results[0]["similarity"] == pytest.approx(1.0)
    assert results[0]["file_name"] == "propio.docx"

    with pytest.raises(HTTPException) as exc_info:
        rag_service.retrieve_for_attachment(
            db_session,
            attachment_id=attachment.id,
            user_id=other_user.id,
            query="consulta",
        )
    assert exc_info.value.status_code == 403


def test_retrieve_for_attachment_missing_document_raises(db_session, test_user):
    with pytest.raises(HTTPException) as exc_info:
        rag_service.retrieve_for_attachment(
            db_session, attachment_id=999999, user_id=test_user.id, query="x"
        )
    assert exc_info.value.status_code == 404


def test_retrieve_context_blank_query_returns_empty(db_session, test_project):
    assert rag_service.retrieve_context(db_session, test_project.id, "   ") == []


def test_retrieve_context_lexical_fallback(db_session, test_project, monkeypatch):
    attachment = _make_attachment(
        db_session, file_name="lexico.docx", project_id=test_project.id
    )
    db_session.add(
        DocumentChunk(
            attachment_id=attachment.id,
            project_id=test_project.id,
            chunk_index=0,
            content="inteligencia artificial en educacion",
            embedding=[0.1] * EMBEDDING_DIMENSION,
            token_count=1,
        )
    )
    db_session.commit()

    def _fail_embedding(_texts):
        raise RAGServiceError("sin embeddings")

    monkeypatch.setattr(rag_service, "embed_texts", _fail_embedding)

    results = rag_service.retrieve_context(
        db_session, project_id=test_project.id, query="inteligencia educacion"
    )

    assert len(results) == 1
    assert results[0]["similarity"] > 0


# -------------------------------------------------------------------- formatting
def test_format_rag_context_includes_metadata():
    chunks = [
        {
            "attachment_id": 1,
            "chunk_index": 3,
            "content": "Texto del fragmento",
            "similarity": 0.83,
            "file_name": "tesis.docx",
        }
    ]

    formatted = rag_service.format_rag_context(chunks)

    assert formatted is not None
    assert "tesis.docx" in formatted
    assert "chunk 3" in formatted
    assert "0.83" in formatted
    assert "Texto del fragmento" in formatted


def test_format_rag_context_returns_none_for_empty():
    assert rag_service.format_rag_context([]) is None


# ------------------------------------------------------------- project resolution
def test_resolve_project_id_from_project_phase_and_task(
    db_session, test_project, test_phase, test_task
):
    project_attachment = _make_attachment(db_session, project_id=test_project.id)
    phase_attachment = _make_attachment(
        db_session, file_name="fase.docx", phase_id=test_phase.id
    )
    task_attachment = _make_attachment(
        db_session, file_name="tarea.docx", task_id=test_task.id
    )

    assert (
        rag_service.resolve_project_id(db_session, project_attachment)
        == test_project.id
    )
    assert (
        rag_service.resolve_project_id(db_session, phase_attachment) == test_project.id
    )
    assert (
        rag_service.resolve_project_id(db_session, task_attachment) == test_project.id
    )


def test_postgres_distance_expression_uses_float_result_type():
    """Regression: the ``<=>`` scalar must be Float, not the Vector column type."""
    from sqlalchemy import Float
    from sqlalchemy.dialects import postgresql

    expression = rag_service._distance_expression([0.1] * 768)

    assert isinstance(expression.type, Float)
    compiled = str(expression.compile(dialect=postgresql.dialect()))
    assert "<=>" in compiled


def test_retrieve_for_attachment_excludes_siblings_in_same_project(
    db_session, test_user, test_project, test_phase, monkeypatch
):
    """The document search endpoint must not return sibling attachment chunks."""
    own = _make_attachment(
        db_session, file_name="propio.docx", project_id=test_project.id
    )
    sibling = _make_attachment(
        db_session, file_name="hermano.docx", phase_id=test_phase.id
    )

    db_session.add_all(
        [
            DocumentChunk(
                attachment_id=own.id,
                project_id=test_project.id,
                chunk_index=0,
                content="contenido propio",
                embedding=_unit_vector(0),
                token_count=1,
            ),
            DocumentChunk(
                attachment_id=sibling.id,
                project_id=test_project.id,
                chunk_index=0,
                content="contenido hermano",
                embedding=_unit_vector(0),
                token_count=1,
            ),
        ]
    )
    db_session.commit()

    monkeypatch.setattr(rag_service, "embed_texts", lambda _texts: [_unit_vector(0)])

    results = rag_service.retrieve_for_attachment(
        db_session,
        attachment_id=own.id,
        user_id=test_user.id,
        query="contenido",
        top_k=5,
    )

    assert len(results) == 1
    assert results[0]["attachment_id"] == own.id
    assert results[0]["content"] == "contenido propio"


def test_retrieve_context_falls_back_to_lexical_with_null_embeddings(
    db_session, test_project, monkeypatch
):
    attachment = _make_attachment(db_session, project_id=test_project.id)
    db_session.add(
        DocumentChunk(
            attachment_id=attachment.id,
            project_id=test_project.id,
            chunk_index=0,
            content="inteligencia artificial en educacion",
            embedding=None,
            token_count=1,
        )
    )
    db_session.commit()

    monkeypatch.setattr(rag_service, "embed_texts", lambda _texts: [_unit_vector(0)])

    results = rag_service.retrieve_context(
        db_session, project_id=test_project.id, query="inteligencia educacion"
    )

    assert len(results) == 1
    assert results[0]["similarity"] > 0


def test_index_attachment_preserves_old_chunks_on_extraction_failure(
    db_session, test_project, monkeypatch
):
    attachment = _make_attachment(db_session, project_id=test_project.id)
    db_session.add(
        DocumentChunk(
            attachment_id=attachment.id,
            project_id=test_project.id,
            chunk_index=0,
            content="indice anterior",
            embedding=[0.1] * EMBEDDING_DIMENSION,
            token_count=1,
        )
    )
    db_session.commit()

    def _fail_extract(_attachment):
        raise RAGServiceError("no se pudo leer el archivo")

    monkeypatch.setattr(rag_service, "extract_text", _fail_extract)

    with pytest.raises(RAGServiceError):
        rag_service.index_attachment(db_session, attachment)

    assert (
        db_session.query(DocumentChunk).filter_by(attachment_id=attachment.id).count()
        == 1
    )


def test_extract_text_rejects_pdf_error_strings(db_session, test_project, monkeypatch):
    attachment = _make_attachment(
        db_session,
        file_name="roto.pdf",
        file_path="/tmp/roto.pdf",
        file_type=FileType.PDF,
        project_id=test_project.id,
    )

    monkeypatch.setattr(
        "app.services.document_extraction_service.document_extraction_service."
        "extract_pdf_to_text",
        lambda *_args, **_kwargs: "Error al extraer PDF: archivo corrupto",
    )

    with pytest.raises(RAGServiceError):
        rag_service.extract_text(attachment)
