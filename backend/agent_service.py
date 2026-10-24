"""LangGraph orchestration service used by the backend's chat endpoint."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from backend.graph import build_graph
from backend.config import MAX_CHAT_HISTORY_MESSAGES
from backend.logging_utils import get_logger
from backend.mcp_client import create_mcp_client
from backend.optics_client import query_optics_rag
from backend.web_artifacts import general_image, source_image


logger = get_logger(__name__)


def _history_to_messages(history: list[dict[str, Any]]) -> list:
    """Convert the frontend's small JSON chat history to LangChain messages."""
    return [
        HumanMessage(content=message["content"])
        if message["role"] == "user"
        else AIMessage(content=message["content"])
        for message in history[-MAX_CHAT_HISTORY_MESSAGES:]
        if message.get("content")
    ]


def _tool_payload(content: Any) -> dict[str, Any] | None:
    """Read JSON from either stdio text or HTTP MCP content blocks."""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "".join(
            item.get("text", "") if isinstance(item, dict) else getattr(item, "text", "")
            for item in content
        )
    else:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _latest_tool_result(messages: list, names: set[str]) -> dict[str, Any] | None:
    """Return the most recent structured output for a named MCP tool."""
    for message in reversed(messages):
        if getattr(message, "name", None) in names:
            payload = _tool_payload(getattr(message, "content", None))
            if payload:
                return payload
    return None


async def run_agent(
    question: str,
    history: list[dict[str, Any]],
    active_source_file: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """Run one request and return the model answer plus UI-only RAG artifacts."""
    logger.info(
        "Backend chat started question_chars=%d history_messages=%d active_source=%s",
        len(question), len(history), active_source_file or "none",
    )
    client = create_mcp_client()
    tools = await client.get_tools()
    logger.info("Backend MCP discovery completed tool_count=%d", len(tools))

    graph = build_graph(tools, active_source_file=active_source_file)
    result = await graph.ainvoke(
        {"messages": [*_history_to_messages(history), HumanMessage(content=question)]}
    )
    answer = result["messages"][-1].content
    rag_result = _latest_tool_result(result["messages"], {"rag_search"})
    if rag_result:
        if not rag_result.get("retrieval_found", True):
            logger.info("Backend chat completed rag_used=true retrieval_found=false")
            return answer, {"sources": [], "image_base64": None}
        artifacts = await asyncio.to_thread(
            query_optics_rag,
            rag_result.get("query", question),
            5,
            rag_result.get("source_file") or active_source_file,
        )
        if not artifacts.get("ok") or not artifacts.get("retrieval_found", True):
            logger.warning("Backend RAG artifacts could not be retrieved")
            return answer, None
        logger.info("Backend chat completed rag_used=true retrieval_found=true")
        return answer, {
            "sources": artifacts.get("sources", []),
            "image_base64": artifacts.get("image_base64"),
        }

    web_result = _latest_tool_result(result["messages"], {"web_search", "scrape_page"})
    if web_result:
        web_image = await asyncio.to_thread(source_image, web_result)
    elif len(question.strip()) > 15:
        # General-answer image fallback. This is optional and never affects the answer.
        web_image = await asyncio.to_thread(general_image, question)
    else:
        web_image = None
    logger.info("Backend chat completed rag_used=false web_image=%s", bool(web_image))
    return answer, {"web_image": web_image} if web_image else None
