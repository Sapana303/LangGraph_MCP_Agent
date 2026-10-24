from mcp_service.tools.rag import search_optics_rag


def test_rag_reports_unavailable_service(monkeypatch):
    monkeypatch.setattr("mcp_service.tools.rag.OPTICS_RAG_API_URL", "http://127.0.0.1:1")
    result = search_optics_rag("What is the leave policy?")
    assert result["ok"] is False
    assert "unavailable" in result["error"]


def test_rag_passes_named_document_filter(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"answer": "Nulla is a sample person.", "citations": [], "retrieval_found": True}

    captured = {}

    def fake_post(*args, **kwargs):
        captured.update(kwargs["json"])
        return Response()

    monkeypatch.setattr("mcp_service.tools.rag.requests.post", fake_post)
    result = search_optics_rag("Who is Nulla?", source_file="sample-local-pdf.pdf")

    assert result["ok"] is True
    assert result["source_file"] == "sample-local-pdf.pdf"
    assert captured["filters"] == {"source_file": "sample-local-pdf.pdf"}
