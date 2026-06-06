import json
import os
import pytest
from unittest.mock import patch, MagicMock
from core.interaction_chain import InteractionChain


def _fake_chain():
    chain = InteractionChain("Test audit query")
    chain.add_step("llm_response", "The model uses Black-Scholes.", 1)
    chain.add_step("evaluator_judgment", json.dumps({"sufficient": True, "confidence": 0.95}), 1)
    chain.final_output = "The model uses Black-Scholes."
    chain.total_iterations = 1
    chain.early_stopped = True
    return chain


@pytest.fixture
def client():
    from web.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_index_returns_200(client):
    r = client.get("/")
    assert r.status_code == 200


def test_health_returns_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    assert "version" in data


def test_list_files_valid_directory(client):
    with patch("web.routes.list_files", return_value=["test.md", "test.xlsx"]):
        r = client.post("/api/list-files",
                        json={"folder_path": "/tmp"},
                        content_type="application/json")
        assert r.status_code == 200
        data = r.get_json()
        assert "files" in data
        assert len(data["files"]) == 2


def test_list_files_invalid_directory(client):
    with patch("web.routes.list_files", side_effect=FileNotFoundError("Not found")):
        r = client.post("/api/list-files",
                        json={"folder_path": os.path.join(os.path.abspath(os.sep), "nonexistent")},
                        content_type="application/json")
        assert r.status_code == 400
        data = r.get_json()
        assert "error" in data


def test_list_files_missing_folder_path(client):
    r = client.post("/api/list-files",
                    json={},
                    content_type="application/json")
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data


def test_list_files_relative_path(client):
    r = client.post("/api/list-files",
                    json={"folder_path": "relative/path"},
                    content_type="application/json")
    assert r.status_code == 400


def test_query_returns_chain(client):
    fake = _fake_chain()
    with patch("web.routes.run_harness", return_value=fake):
        r = client.post("/api/query",
                        json={"query": "Audit this model."},
                        content_type="application/json")
        assert r.status_code == 200
        data = r.get_json()
        assert "final_output" in data
        assert data["total_iterations"] == 1
        assert data["early_stopped"] is True


def test_query_missing_query(client):
    r = client.post("/api/query",
                    json={},
                    content_type="application/json")
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data


def test_query_with_files(client):
    fake = _fake_chain()
    with patch("web.routes.run_harness", return_value=fake), \
         patch("web.routes.read_file", return_value={"filename": "doc.md", "content": "file content"}):
        r = client.post("/api/query",
                        json={
                            "query": "Audit with docs.",
                            "folder_path": "/tmp",
                            "selected_files": ["doc.md"],
                        },
                        content_type="application/json")
        assert r.status_code == 200


def test_export_creates_file(client, tmp_path):
    fake = _fake_chain()
    chain_dict = fake.to_dict()

    r = client.post("/api/export",
                    json={
                        "chain_data": chain_dict,
                        "folder_path": str(tmp_path),
                    },
                    content_type="application/json")
    assert r.status_code == 200
    data = r.get_json()
    assert "filename" in data
    assert "path" in data
    assert (tmp_path / "exports" / data["filename"]).exists()


def test_export_default_location(client):
    fake = _fake_chain()
    chain_dict = fake.to_dict()

    with patch("web.routes.Path") as mock_path:
        mock_export_dir = MagicMock()
        mock_path.return_value.parent.parent = MagicMock()
        mock_path.return_value.parent.parent.__truediv__ = MagicMock(return_value=mock_export_dir)

        r = client.post("/api/export",
                        json={"chain_data": chain_dict},
                        content_type="application/json")
        assert r.status_code == 200


def test_export_missing_chain_data(client):
    r = client.post("/api/export",
                    json={},
                    content_type="application/json")
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data


def test_error_response_is_json(client):
    r = client.post("/api/list-files",
                    json={"folder_path": "relative"},
                    content_type="application/json")
    assert "application/json" in r.content_type


def test_export_rejects_relative_path(client):
    """BF-3: Export endpoint must reject relative folder_path."""
    fake = _fake_chain()
    r = client.post("/api/export",
                    json={"chain_data": fake.to_dict(), "folder_path": "relative/path"},
                    content_type="application/json")
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data


def test_export_rejects_nonexistent_path(client):
    """BF-3: Export endpoint must reject nonexistent folder_path."""
    fake = _fake_chain()
    r = client.post("/api/export",
                    json={"chain_data": fake.to_dict(), "folder_path": os.path.join(os.path.abspath(os.sep), "nonexistent", "path", "12345")},
                    content_type="application/json")
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data
