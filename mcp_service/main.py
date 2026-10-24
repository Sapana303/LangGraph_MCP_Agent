"""One independently runnable MCP server that exposes all agent tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_service.config import MCP_SERVER_HOST, MCP_SERVER_PORT
from mcp_service.logging_utils import get_logger
from mcp_service.tools.filesystem import list_directory
from mcp_service.tools.rag import search_optics_rag
from mcp_service.tools.resume_matcher import rank_resumes_against_jd
from mcp_service.tools.scraper import scrape_webpage
from mcp_service.tools.weather import get_weather
from mcp_service.tools.web_search import search_web


logger = get_logger(__name__)
mcp = FastMCP(
    "LangGraph MCP Tool Service",
    instructions="A local tool service for files, weather, web research, document RAG, and webpage reading.",
    host=MCP_SERVER_HOST,
    port=MCP_SERVER_PORT,
)


@mcp.tool()
def list_files(
    directory: str,
    recursive: bool = False,
    extension: str | None = None,
) -> dict:
    """List files and folders inside the LangGraph_MCP_Agent project.

    The project root is the filesystem boundary.

    Examples:
    - "." -> project root
    - "backend" -> backend directory
    - "frontend" -> frontend directory
    - "mcp_service" -> MCP service
    - "mcp_service/tools" -> MCP tools
    - "logs" -> project logs
    - "data" -> data directory

    Set recursive=True to inspect nested files.

    This tool returns file metadata only.
    It does not read file contents.
    """
    return list_directory(directory, recursive, extension)

@mcp.tool()
def weather(location: str) -> dict:
    """Get current weather conditions for a named city, town, or location."""
    return get_weather(location)


@mcp.tool()
def web_search(query: str, max_results: int = 5, domain: str | None = None) -> dict:
    """Search the public web for current or external information.

    Use scrape_page afterward when a result page needs to be read in detail.
    """
    return search_web(query, max_results, domain)


@mcp.tool()
def rag_search(query: str, top_k: int = 5, source_file: str | None = None) -> dict:
    """Search uploaded, indexed internal documents through Optics RAG.

    Use source_file when the user asks about one particular uploaded document.
    """
    return search_optics_rag(query, top_k, source_file)


@mcp.tool()
def scrape_page(url: str) -> dict:
    """Read and clean the visible text from a specific public HTTP or HTTPS webpage."""
    return scrape_webpage(url)


@mcp.tool()
def match_resumes(resume_directory: str, job_description: str, max_results: int = 5) -> dict:
    """Score resumes in a directory against a job description and suggest skill gaps.

    Use this when the user has many resumes and wants to find the closest match.
    """
    return rank_resumes_against_jd(resume_directory, job_description, max_results)


if __name__ == "__main__":
    logger.info(
        "Starting MCP tool service host=%s port=%d transport=streamable_http tool_count=5",
        MCP_SERVER_HOST,
        MCP_SERVER_PORT,
    )
    mcp.run(transport="streamable-http")
