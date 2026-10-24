"""HTTP client used by the terminal UI to call the FastAPI backend."""

from __future__ import annotations

import requests

from backend.config import BACKEND_API_URL


class BackendUnavailableError(RuntimeError):
    """Raised when the independently running backend cannot answer a request."""


def ask_backend(question: str, history: list[dict], active_source_file: str | None) -> tuple[str, dict | None]:
    """Send one chat request to the backend and return its answer/artifacts."""
    try:
        response = requests.post(
            f"{BACKEND_API_URL}/chat",
            json={
                "question": question,
                "history": [{"role": item["role"], "content": item["content"]} for item in history],
                "active_source_file": active_source_file,
            },
            timeout=180,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["answer"], payload.get("artifacts")
    except (KeyError, ValueError, requests.RequestException) as error:
        raise BackendUnavailableError("The LangGraph backend is unavailable.") from error


def ingest_document(filename: str, content: bytes, content_type: str | None) -> dict:
    """Forward a document to the backend, which sends it to Optics RAG."""
    try:
        response = requests.post(
            f"{BACKEND_API_URL}/documents",
            files={"file": (filename, content, content_type or "application/octet-stream")},
            timeout=600,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        raise BackendUnavailableError("The backend could not index the document.") from error
