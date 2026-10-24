from __future__ import annotations

import asyncio
import os
from ipaddress import ip_address
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from mcp_service.logging_utils import get_logger


logger = get_logger(__name__)


def _crawl_dynamic_page(url: str) -> dict | None:
    """Optional Crawl4AI fallback for JavaScript pages; static scraping remains primary."""
    if os.getenv("CRAWL4AI_ENABLED", "false").lower() != "true":
        return None
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        async def crawl() -> dict | None:
            browser = BrowserConfig(headless=True)
            run = CrawlerRunConfig(page_timeout=30_000)
            async with AsyncWebCrawler(config=browser) as crawler:
                result = await crawler.arun(url=url, config=run)
            markdown = getattr(result, "markdown", "")
            if not markdown:
                return None
            return {"ok": True, "url": url, "title": getattr(result, "title", "Untitled page"), "content": markdown[:12000], "crawler": "crawl4ai"}

        logger.info("Crawler fallback started host=%s", urlparse(url).hostname or "unknown")
        return asyncio.run(crawl())
    except ImportError:
        logger.warning("Crawler fallback skipped reason=crawl4ai_not_installed")
        return None
    except Exception as error:
        logger.warning("Crawler fallback failed error_type=%s", type(error).__name__)
        return None


def scrape_webpage(url: str) -> dict:
    parsed = urlparse(url)
    host = parsed.hostname or "unknown"
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        logger.warning("Scraper rejected request reason=invalid_url")
        return {"ok": False, "error": "Provide a valid http or https URL."}
    logger.info("Scraper request started host=%s scheme=%s", host, parsed.scheme)
    try:
        address = ip_address(parsed.hostname or "")
        if address.is_private or address.is_loopback or address.is_link_local:
            logger.warning("Scraper rejected request reason=private_address host=%s", host)
            return {"ok": False, "error": "Private-network URLs cannot be scraped."}
    except ValueError:
        pass  # Hostname rather than a literal IP address.
    try:
        robots_url = urljoin(url, "/robots.txt")
        robots_response = requests.get(robots_url, timeout=5, headers={"User-Agent": "LangGraph-MCP-Agent/1.0"})
        if robots_response.ok:
            robots = RobotFileParser()
            robots.parse(robots_response.text.splitlines())
            if not robots.can_fetch("LangGraph-MCP-Agent", url):
                logger.warning("Scraper rejected request reason=robots_disallow host=%s", host)
                return {"ok": False, "error": "This page disallows automated access in robots.txt."}
        response = requests.get(url, timeout=15, headers={"User-Agent": "LangGraph-MCP-Agent/1.0"})
        response.raise_for_status()
        if "text/html" not in response.headers.get("content-type", "").lower():
            logger.warning("Scraper failed reason=non_html_response host=%s", host)
            return {"ok": False, "error": "The URL did not return an HTML page."}
        soup = BeautifulSoup(response.text, "html.parser")
        for element in soup(["script", "style", "noscript", "nav", "footer", "header", "aside", "form"]):
            element.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else "Untitled page"
        main = soup.find("main") or soup.find("article") or soup.body
        content = main.get_text(" ", strip=True) if main else ""
        if not content:
            logger.warning("Scraper failed reason=no_readable_text host=%s", host)
            dynamic_result = _crawl_dynamic_page(url)
            if dynamic_result:
                return dynamic_result
            return {"ok": False, "error": "The page did not contain readable text."}
        logger.info("Scraper request completed host=%s content_chars=%d", host, len(content))
        return {"ok": True, "url": url, "title": title, "content": content[:12000]}
    except requests.Timeout:
        logger.warning("Scraper request timed_out host=%s", host)
        return {"ok": False, "error": "The website timed out."}
    except requests.RequestException as error:
        logger.warning("Scraper request failed host=%s error_type=%s", host, type(error).__name__)
        dynamic_result = _crawl_dynamic_page(url)
        if dynamic_result:
            return dynamic_result
        return {"ok": False, "error": f"Could not fetch webpage: {error}"}
