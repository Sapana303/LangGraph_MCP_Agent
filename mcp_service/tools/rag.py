from __future__ import annotations

import requests

from mcp_service.config import OPTICS_RAG_API_URL
from mcp_service.logging_utils import get_logger


logger = get_logger(__name__)


def search_optics_rag(query: str, top_k: int = 5, source_file: str | None = None) -> dict:
    """Return the compact RAG result sent to the LLM through MCP."""
    result = query_optics_rag(query, top_k, source_file)
    if not result["ok"]:
        return result
    return {
        "ok": True,
        "query": query,
        "source_file": source_file,
        "answer": result["answer"],
        "sources": result["sources"],
        "image_available": bool(result.get("image_base64")),
        "retrieval_found": result.get("retrieval_found", True),
    }


def query_optics_rag(query: str, top_k: int = 5, source_file: str | None = None) -> dict:
    """Query Optics directly, retaining its optional image for the UI artifact renderer."""
    try:
        logger.info(
            "Optics RAG query started query_chars=%d top_k=%d source_file=%s",
            len(query), top_k, source_file or "all_documents",
        )
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
        logger.info(
            "Optics RAG query completed retrieval_found=%s citation_count=%d",
            payload.get("retrieval_found", True), len(payload.get("citations", [])),
        )
        return {
            "ok": True,
            "query": query,
            "answer": payload.get("answer", ""),
            "sources": payload.get("citations", []),
            "image_base64": payload.get("image_base64"),
            "retrieval_found": payload.get("retrieval_found", True),
        }
    except requests.RequestException as error:
        logger.warning("Optics RAG query failed error_type=%s", type(error).__name__)
        return {
            "ok": False,
            "error": "Optics RAG is unavailable. Start its FastAPI service before asking document questions.",
            "detail": str(error),
        }
