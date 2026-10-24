from mcp_service.tools.scraper import scrape_webpage


def test_rejects_invalid_url():
    result = scrape_webpage("not-a-url")
    assert result["ok"] is False
    assert "valid http" in result["error"]
