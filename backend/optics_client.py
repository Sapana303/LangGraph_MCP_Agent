"""Small HTTP client for the separate Optics RAG service."""

from __future__ import annotations

import requests

from backend.config import OPTICS_RAG_API_URL
from backend.logging_utils import get_logger


logger = get_logger(__name__)


def ingest_document(filename: str, content: bytes, content_type: str | None) -> dict:
    """Forward a React-uploaded document through FastAPI to Optics RAG.

    Critical backend -> Optics boundary: the browser never contacts RAG directly.
    """
    logger.info("Backend document ingestion started filename=%s size_bytes=%d", filename, len(content))
    response = requests.post(
        f"{OPTICS_RAG_API_URL}/ingest",
        files={"file": (filename, content, content_type or "application/octet-stream")},
        timeout=600,
    )
    response.raise_for_status()
    result = response.json()
    logger.info("Backend document ingestion completed filename=%s chunks_added=%s", filename, result.get("chunks_added", "unknown"))
    return result


def query_optics_rag(query: str, top_k: int = 5, source_file: str | None = None) -> dict:
    """Fetch UI artifacts from Optics after the agent actually used the RAG MCP tool."""
    try:
        response = requests.post(
            f"{OPTICS_RAG_API_URL}/query",
            json={
                "question": query,
                "top_k": max(1, min(top_k, 10)),
                "filters": {"source_file": source_file} if source_file else None,
            },
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        return {
            "ok": True,
            "sources": payload.get("citations", []),
            "image_base64": payload.get("image_base64"),
            "retrieval_found": payload.get("retrieval_found", True),
        }
    except requests.RequestException as error:
        logger.warning("Backend Optics artifact query failed error_type=%s", type(error).__name__)
        return {"ok": False, "error": "Optics RAG is unavailable."}
