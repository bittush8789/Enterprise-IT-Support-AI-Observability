import io
import json
import sqlite3
from unittest.mock import patch, MagicMock
import pytest
from app.core.config import get_settings

settings = get_settings()


class TestAPIEndpoints:
    """
    Tests all FastAPI REST endpoints with external LLM and vectorstore calls mocked.
    """

    def test_health_endpoint(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == settings.app_name

    def test_frontend_home_page(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "NovaRetail" in response.text or "IT Support" in response.text

    @patch("app.api.routes.ask")
    def test_chat_endpoint_success(self, mock_ask, client, mock_agent_result):
        mock_ask.return_value = mock_agent_result

        payload = {"question": "How do I connect to VPN from home?"}
        response = client.post("/api/chat", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == mock_agent_result["answer"]
        assert data["source_used"] == "private_kb"
        assert len(data["trace"]) == len(mock_agent_result["trace"])
        assert len(data["citations"]) == 1
        assert data["rewritten_query"] == "How do I connect to VPN?"
        mock_ask.assert_called_once_with("How do I connect to VPN from home?")

    def test_chat_endpoint_validation_errors(self, client):
        # Empty question string (< 2 chars min_length)
        res_empty = client.post("/api/chat", json={"question": ""})
        assert res_empty.status_code == 422

        # 1 character question (< 2 chars min_length)
        res_short = client.post("/api/chat", json={"question": "?"})
        assert res_short.status_code == 422

        # Missing body field
        res_missing = client.post("/api/chat", json={})
        assert res_missing.status_code == 422

    @patch("app.api.routes.ask")
    def test_chat_endpoint_handles_workflow_error(self, mock_ask, client):
        mock_ask.side_effect = RuntimeError("External LLM connection timeout")

        payload = {"question": "What is the password policy?"}
        response = client.post("/api/chat", json=payload)

        assert response.status_code == 500
        assert "External LLM connection timeout" in response.json()["detail"]

    @patch("app.api.routes.ask")
    def test_chat_audit_logging(self, mock_ask, client, mock_agent_result):
        mock_ask.return_value = mock_agent_result

        test_question = "How do I reset my MFA password?"
        response = client.post("/api/chat", json={"question": test_question})
        assert response.status_code == 200

        # Query the audit database to ensure record was written
        con = sqlite3.connect(settings.audit_db_path)
        cur = con.cursor()
        cur.execute("SELECT question, source_used, trace_json FROM query_audit WHERE question = ?", (test_question,))
        row = cur.fetchone()
        con.close()

        assert row is not None, "Audit record was not written to SQLite database"
        assert row[0] == test_question
        assert row[1] == "private_kb"
        trace_saved = json.loads(row[2])
        assert isinstance(trace_saved, list)
        assert len(trace_saved) > 0

    def test_ingest_unauthorized_without_admin_key(self, client):
        file_bytes = io.BytesIO(b"# Policy\nSome text")
        files = {"file": ("policy.md", file_bytes, "text/markdown")}

        # No header
        res_no_key = client.post("/api/ingest", files=files)
        assert res_no_key.status_code == 401
        assert "Invalid admin key" in res_no_key.json()["detail"]

        # Wrong header
        file_bytes.seek(0)
        res_bad_key = client.post("/api/ingest", files=files, headers={"x-admin-key": "wrong-key"})
        assert res_bad_key.status_code == 401

    def test_ingest_unsupported_extension(self, client):
        file_bytes = io.BytesIO(b"print('hello')")
        files = {"file": ("script.py", file_bytes, "text/plain")}
        headers = {"x-admin-key": settings.admin_api_key}

        response = client.post("/api/ingest", files=files, headers=headers)
        assert response.status_code == 400
        assert "Supported" in response.json()["detail"]

    @patch("app.api.routes.add_documents")
    def test_ingest_success(self, mock_add_docs, client, tmp_path, monkeypatch):
        mock_add_docs.return_value = ["vec-id-1", "vec-id-2"]
        upload_dir = tmp_path / "test_uploads"
        monkeypatch.setattr(settings, "upload_dir", str(upload_dir))

        file_content = b"# New Wifi Policy\nAll guests must connect to NovaGuest wifi."
        files = {"file": ("wifi_policy.md", io.BytesIO(file_content), "text/markdown")}
        headers = {"x-admin-key": settings.admin_api_key}

        response = client.post("/api/ingest", files=files, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Document indexed"
        assert data["file"] == "wifi_policy.md"
        assert data["chunks"] >= 1
        assert data["ids_created"] == 2
        mock_add_docs.assert_called_once()
