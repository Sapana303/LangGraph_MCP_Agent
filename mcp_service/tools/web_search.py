from __future__ import annotations

import os
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from mcp_service.logging_utils import get_logger


logger = get_logger(__name__)


def search_web(query: str, max_results: int = 5, domain: str | None = None) -> dict:
    api_key = os.getenv("TAVILY_API_KEY")
    logger.info(
        "Web search started query_chars=%d max_results=%d provider=%s domain=%s",
        len(query), max_results, "tavily" if api_key else "duckduckgo", domain or "none",
    )
    if not api_key:
        return _search_duckduckgo(query, max_results, domain)
    try:
        payload = {"api_key": api_key, "query": query, "max_results": max(1, min(max_results, 10))}
        if domain:
            payload["include_domains"] = [domain]
        response = requests.post("https://api.tavily.com/search", json=payload, timeout=15)
        response.raise_for_status()
        results = [
            {"title": item.get("title"), "url": item.get("url"), "snippet": item.get("content", "")}
            for item in response.json().get("results", [])
        ]
        logger.info("Web search completed provider=tavily result_count=%d", len(results))
        return {"ok": True, "provider": "tavily", "query": query, "results": results}
    except requests.RequestException as error:
        logger.warning("Web search failed provider=tavily error_type=%s", type(error).__name__)
        return {"ok": False, "error": f"Web search failed: {error}", "results": []}


def _search_duckduckgo(query: str, max_results: int, domain: str | None) -> dict:
    """Search DuckDuckGo's public HTML endpoint when no authenticated provider is configured."""
    search_query = f"site:{domain} {query}" if domain else query
    try:
        response = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": search_query},
            headers={"User-Agent": "LangGraph-MCP-Agent/1.0"},
            timeout=15,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        for result in soup.select(".result"):
            anchor = result.select_one(".result__a")
            if not anchor or not anchor.get("href"):
                continue
            href = _resolve_duckduckgo_url(anchor["href"])
            snippet = result.select_one(".result__snippet")
            results.append(
                {
                    "title": anchor.get_text(" ", strip=True),
                    "url": href,
                    "snippet": snippet.get_text(" ", strip=True) if snippet else "",
                }
            )
            if len(results) >= max(1, min(max_results, 10)):
                break
        if not results:
            logger.warning("Web search completed provider=duckduckgo result_count=0")
            return {"ok": False, "error": "The public search provider returned no results.", "results": []}
        logger.info("Web search completed provider=duckduckgo result_count=%d", len(results))
        return {"ok": True, "provider": "duckduckgo", "query": query, "results": results}
    except requests.RequestException as error:
        logger.warning("Web search failed provider=duckduckgo error_type=%s", type(error).__name__)
        return {"ok": False, "error": f"Web search failed: {error}", "results": []}


def _resolve_duckduckgo_url(href: str) -> str:
    """Extract the destination URL from DuckDuckGo's optional redirect link."""
    parsed = urlparse(href)
    destination = parse_qs(parsed.query).get("uddg", [None])[0]
    return unquote(destination) if destination else href
