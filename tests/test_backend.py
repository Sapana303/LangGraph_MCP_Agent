from fastapi.testclient import TestClient

from backend.agent_service import _tool_payload
from backend.main import app


def test_backend_health_endpoint():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "langgraph-backend"}


def test_backend_rejects_empty_question_before_agent_execution():
    response = TestClient(app).post("/chat", json={"question": "", "history": []})

    assert response.status_code == 422


def test_backend_forwards_document_upload_to_optics(monkeypatch):
    captured = {}

    def fake_ingest(filename, content, content_type):
        captured.update(filename=filename, content=content, content_type=content_type)
        return {"filename": filename, "chunks_added": 3}

    monkeypatch.setattr("backend.main.ingest_document", fake_ingest)
    response = TestClient(app).post(
        "/documents",
        files={"file": ("notes.md", b"# Notes", "text/markdown")},
    )

    assert response.status_code == 200
    assert response.json() == {"filename": "notes.md", "chunks_added": 3}
    assert captured == {"filename": "notes.md", "content": b"# Notes", "content_type": "text/markdown"}


def test_backend_reads_json_from_http_mcp_content_blocks():
    payload = _tool_payload([{"type": "text", "text": '{"retrieval_found": true}'}])

    assert payload == {"retrieval_found": True}


def test_backend_persists_chat_and_artifacts(monkeypatch, tmp_path):
    monkeypatch.setattr("backend.conversation_store.DATABASE_PATH", tmp_path / "history.db")

    async def fake_run_agent(question, history, active_source_file):
        assert question == "What is attenuation?"
        assert history == []
        assert active_source_file is None
        return "A reduction in signal strength.", {"sources": [{"source_file": "notes.pdf", "page": 2}]}

    monkeypatch.setattr("backend.main.run_agent", fake_run_agent)
    with TestClient(app) as client:
        response = client.post("/chat", json={"question": "What is attenuation?"})
        assert response.status_code == 200
        body = response.json()
        saved = client.get(f"/conversations/{body['conversation_id']}")

    assert saved.status_code == 200
    assert saved.json()["messages"] == [
        {"role": "user", "content": "What is attenuation?", "artifacts": None},
        {
            "role": "assistant",
            "content": "A reduction in signal strength.",
            "artifacts": {"sources": [{"source_file": "notes.pdf", "page": 2}]},
        },
    ]


def test_backend_accepts_safe_react_diagnostic_event():
    response = TestClient(app).post("/client-events", json={"event": "chat_failed", "detail": "NETWORK_ERROR"})

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
