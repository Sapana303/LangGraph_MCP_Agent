from mcp_service.tools.filesystem import list_directory


def test_lists_sample_documents():
    result = list_directory("./data/documents")
    assert result["ok"] is True
    assert any(entry["path"].endswith("employee_handbook.md") for entry in result["entries"])


def test_rejects_paths_outside_data_root():
    result = list_directory("../")
    assert result["ok"] is False
    assert "limited" in result["error"]
