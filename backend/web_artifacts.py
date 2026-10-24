"""Extract a credited page image for answers grounded in public web tools."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from backend.logging_utils import get_logger


logger = get_logger(__name__)


def source_image(tool_result: dict[str, Any]) -> dict[str, str] | None:
    """Find an og:image from the first selected result; never invent an image source."""
    url = tool_result.get("url")
    if not url:
        results = tool_result.get("results", [])
        url = results[0].get("url") if results else None
    if not isinstance(url, str) or urlparse(url).scheme not in {"http", "https"}:
        return None
    try:
        response = requests.get(url, headers={"User-Agent": "LangGraph-MCP-Agent/1.0"}, timeout=12)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        tag = soup.select_one('meta[property="og:image"], meta[name="twitter:image"]')
        image_url = tag.get("content") if tag else None
        if not image_url:
            return None
        logger.info("Web image artifact found source_host=%s", urlparse(url).hostname or "unknown")
        return {
            "image_url": urljoin(url, image_url),
            "source_url": url,
            "caption": soup.title.get_text(" ", strip=True) if soup.title else "Related web image",
        }
    except requests.RequestException as error:
        logger.info("Web image artifact unavailable error_type=%s", type(error).__name__)
        return None


def general_image(query: str) -> dict[str, str] | None:
    """Find an attributed optional image for a non-RAG knowledge answer.

    Wikimedia is used as a lightweight public fallback. A missing image must never
    change or fail the underlying agent answer.
    """
    try:
        response = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": query[:160],
                "gsrlimit": 1,
                "prop": "pageimages|info",
                "piprop": "original",
                "inprop": "url",
            },
            headers={"User-Agent": "LangGraph-MCP-Agent/1.0"},
            timeout=8,
        )
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", {})
        page = next(iter(pages.values()), None)
        image_url = page.get("original", {}).get("source") if page else None
        if not image_url:
            return None
        logger.info("General image artifact found source=wikimedia")
        return {
            "image_url": image_url,
            "source_url": page.get("fullurl") or f"https://en.wikipedia.org/wiki/{quote(page.get('title', ''))}",
            "caption": page.get("title", "Related reference image"),
        }
    except (requests.RequestException, ValueError, AttributeError) as error:
        logger.info("General image artifact unavailable error_type=%s", type(error).__name__)
        return None
