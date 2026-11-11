#!/usr/bin/env python3
"""Smoke test for the document RAG pipeline against a running API.

Flow:
  1. GET /health
  2. Register (or login if the user already exists)
  3. Create a project
  4. Upload a DOCX
  5. Poll GET /api/v1/documentos/{id}/search until chunks are indexed
  6. POST /api/v1/proyectos/{id}/chat (RAG context)
  7. POST /api/v1/ia/sugerencias (RAG context)

The API access token can expire while the script waits for the worker (some
environments use ACCESS_TOKEN_EXPIRE_MINUTES=1); every authenticated request is
retried once after a re-login when it returns 401.

Required environment:
  API_BASE_URL   e.g. https://investi-flow-staging.onrender.com

Optional environment:
  TEST_EMAIL, TEST_PASSWORD, TEST_PHONE, TEST_FULL_NAME, DOCX_PATH,
  INDEX_TIMEOUT, TOP_K, TEST_QUERY, CHAT_QUESTION, CLEANUP

Examples:
  API_BASE_URL=http://127.0.0.1:8000 .venv/bin/python \
      scripts/staging_rag_smoke_test.py

  API_BASE_URL=https://<staging>.onrender.com CLEANUP=1 \
      .venv/bin/python scripts/staging_rag_smoke_test.py
"""

import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
EMAIL = os.getenv("TEST_EMAIL", "staging.rag.smoke@example.com")
PASSWORD = os.getenv("TEST_PASSWORD", "RagSmoke123")
PHONE = os.getenv("TEST_PHONE", "+573001112233")
FULL_NAME = os.getenv("TEST_FULL_NAME", "Staging RAG Smoke")
DOCX_PATH = Path(os.getenv("DOCX_PATH", "Planteamiento del problema.docx"))
INDEX_TIMEOUT = int(os.getenv("INDEX_TIMEOUT", "90"))
TOP_K = int(os.getenv("TOP_K", "5"))
CLEANUP = os.getenv("CLEANUP", "0").strip().lower() in ("1", "true", "yes")
QUERY = os.getenv(
    "TEST_QUERY",
    "¿Cuál es el planteamiento del problema y cuáles son sus causas principales?",
)
CHAT_QUESTION = os.getenv(
    "CHAT_QUESTION",
    "Resume el planteamiento del problema del documento y menciona las causas principales.",
)


def _fail(message: str, response: httpx.Response | None = None) -> int:
    print(f"FAIL: {message}")
    if response is not None:
        print(f"  status={response.status_code}")
        print(f"  body={response.text[:800]}")
    return 1


def _login(client: httpx.Client, quiet: bool = False) -> dict[str, str] | None:
    login = client.post(
        "/api/v1/auth/login",
        data={"username": EMAIL, "password": PASSWORD},
    )
    if login.status_code != 200:
        _fail("login falló", login)
        return None
    print("login: refreshed" if quiet else "login: OK")
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _read_docx_text(path: Path, limit: int = 2000) -> str:
    try:
        from docx import Document

        paragraphs = [
            paragraph.text.strip()
            for paragraph in Document(str(path)).paragraphs
            if paragraph.text and paragraph.text.strip()
        ]
        return "\n".join(paragraphs)[:limit]
    except Exception:
        return "El planteamiento del problema de esta investigación se centra en"


def main() -> int:  # noqa: C901
    print(f"API_BASE_URL={API_BASE_URL}")
    print(f"DOCX={DOCX_PATH} exists={DOCX_PATH.exists()}")
    if not DOCX_PATH.exists():
        return _fail(f"No existe el DOCX: {DOCX_PATH}")

    with httpx.Client(
        base_url=API_BASE_URL,
        timeout=120.0,
        follow_redirects=True,
    ) as client:
        try:
            health = client.get("/health")
        except httpx.HTTPError as exc:
            return _fail(f"No se pudo conectar a la API: {exc}")
        print("health:", health.status_code, health.text[:200])
        if health.status_code != 200:
            return _fail("health no devolvió 200", health)

        register_payload: dict[str, Any] = {
            "email": EMAIL,
            "full_name": FULL_NAME,
            "password": PASSWORD,
            "phone_number": PHONE,
            "university": "Staging",
            "career": "Investigación",
        }
        register = client.post("/api/v1/auth/register", json=register_payload)
        if register.status_code in (200, 201):
            print("register: OK")
        elif register.status_code in (400, 409):
            print("register: el usuario ya existe, se intenta login")
        else:
            return _fail("register falló", register)

        headers = _login(client)
        if headers is None:
            return 1

        def call(method: str, url: str, **kwargs: Any) -> httpx.Response:
            """Authenticated request with one re-login retry on 401."""
            nonlocal headers
            response = client.request(method, url, headers=headers, **kwargs)
            if response.status_code == 401:
                refreshed = _login(client, quiet=True)
                if refreshed is None:
                    return response
                headers = refreshed
                response = client.request(method, url, headers=headers, **kwargs)
            return response

        project_payload = {
            "name": f"RAG Staging Smoke {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "description": (
                "Proyecto temporal para validar el pipeline RAG de documentos "
                "con worker real en staging."
            ),
            "research_type": "experimental",
            "institution": "Staging",
            "status": "in_progress",
        }
        project_response = call("POST", "/api/v1/proyectos/", json=project_payload)
        if project_response.status_code not in (200, 201):
            return _fail("creación de proyecto falló", project_response)
        project = project_response.json()
        project_id = project["id"]
        print("project_id:", project_id, "name:", project.get("name"))

        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        with DOCX_PATH.open("rb") as handle:
            upload = call(
                "POST",
                f"/api/v1/proyectos/{project_id}/documentos",
                files={"file": (DOCX_PATH.name, handle, mime)},
            )
        if upload.status_code not in (200, 201):
            return _fail("upload del DOCX falló", upload)
        attachment = upload.json()
        attachment_id = attachment["id"]
        print(
            "attachment_id:",
            attachment_id,
            "file:",
            attachment.get("file_name"),
            "size:",
            attachment.get("file_size"),
        )

        results: list[dict[str, Any]] = []
        deadline = time.time() + INDEX_TIMEOUT
        while time.time() < deadline:
            search = call(
                "GET",
                f"/api/v1/documentos/{attachment_id}/search",
                params={"q": QUERY, "top_k": TOP_K},
            )
            if search.status_code == 404:
                return _fail(
                    "El endpoint /documentos/{id}/search devolvió 404: "
                    "la API desplegada no tiene la rama RAG.",
                    search,
                )
            if search.status_code == 200:
                results = search.json().get("results", [])
                if results:
                    break
            else:
                print("search:", search.status_code, search.text[:300])
            time.sleep(2)

        if not results:
            return _fail(
                f"Sin chunks después de {INDEX_TIMEOUT}s. Revisá que la API y el "
                "worker usen el mismo broker (CELERY_*), que el worker esté "
                "corriendo y que RAG_INDEXING_ENABLED=true."
            )

        print(f"search: {len(results)} resultados para {QUERY!r}")
        for item in results:
            similarity = float(item.get("similarity", 0.0))
            content = str(item.get("content", "")).replace("\n", " ")[:140]
            print(
                f"  - {item.get('file_name')} chunk={item.get('chunk_index')} "
                f"sim={similarity:.3f} :: {content}"
            )

        chat_payload = {
            "message": CHAT_QUESTION,
            "project_context": {
                "project_id": project_id,
                "title": project.get("name"),
                "description": project.get("description"),
            },
        }
        chat = call(
            "POST",
            f"/api/v1/proyectos/{project_id}/chat",
            json=chat_payload,
        )
        if chat.status_code != 200:
            return _fail("chat con RAG falló", chat)
        chat_data = chat.json()
        print(
            "chat: model=",
            chat_data.get("model_used"),
            "conversation_id=",
            chat_data.get("conversation_id"),
        )
        print("chat response:", str(chat_data.get("response", ""))[:1200])

        suggestion_payload = {
            "editor_state": {
                "text": "El planteamiento del problema de esta investigación se centra en",
                "full_document_content": _read_docx_text(DOCX_PATH),
            },
            "bibliography": [],
            "project_info": {
                "project_id": project_id,
                "project_name": project.get("name"),
                "description": project.get("description"),
            },
        }
        suggestion = call(
            "POST",
            "/api/v1/ia/sugerencias",
            json=suggestion_payload,
        )
        if suggestion.status_code != 200:
            print("suggestion: FAIL", suggestion.status_code, suggestion.text[:500])
        else:
            suggestion_data = suggestion.json()
            print("suggestion: model=", suggestion_data.get("model_used"))
            print(
                "suggestion text:",
                str(suggestion_data.get("suggestion", ""))[:900],
            )

        if CLEANUP:
            # The hard delete requires the project to be archived first.
            archive = call("DELETE", f"/api/v1/proyectos/{project_id}")
            print("cleanup archive:", archive.status_code)
            if archive.status_code in (200, 204):
                cleanup = call(
                    "DELETE",
                    f"/api/v1/proyectos/{project_id}/permanent",
                )
                print("cleanup project:", cleanup.status_code)
            else:
                print("cleanup skipped: archive failed", archive.text[:300])

        print("SMOKE TEST OK")
        return 0


if __name__ == "__main__":
    sys.exit(main())
