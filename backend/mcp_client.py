"""Connect the LangGraph backend to the independent MCP tool service."""

from __future__ import annotations

from langchain_mcp_adapters.client import MultiServerMCPClient

from backend.config import MCP_SERVER_URL
from backend.logging_utils import get_logger


logger = get_logger(__name__)


def create_mcp_client() -> MultiServerMCPClient:
    """Create an HTTP MCP client; the backend never starts tool subprocesses.

    Critical backend -> MCP boundary: LangGraph discovers schemas and calls this
    independently running service over HTTP.
    """
    logger.info("Creating MCP HTTP client endpoint=%s", MCP_SERVER_URL)
    return MultiServerMCPClient(
        {
            "tool_service": {
                "transport": "streamable_http",
                "url": MCP_SERVER_URL,
                "timeout": 45,
                "sse_read_timeout": 60 * 5,
            },
        }
    )
