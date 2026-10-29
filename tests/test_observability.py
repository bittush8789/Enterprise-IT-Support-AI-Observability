import pytest
from app.core.config import get_settings
from app.core.observability import (
    is_langfuse_enabled,
    get_langfuse_handler,
    get_trace_url_safe,
    get_observability_status,
)

settings = get_settings()


class TestObservability:
    """
    Unit tests for Langfuse observability integration and helper utilities.
    """

    def test_observability_disabled_by_default_without_keys(self, monkeypatch):
        monkeypatch.setattr(settings, "langfuse_public_key", "")
        monkeypatch.setattr(settings, "langfuse_secret_key", "")
        assert is_langfuse_enabled() is False
        assert get_langfuse_handler() is None

    def test_observability_enabled_with_keys(self, monkeypatch):
        monkeypatch.setattr(settings, "enable_langfuse", True)
        monkeypatch.setattr(settings, "langfuse_public_key", "pk-lf-test-123456789")
        monkeypatch.setattr(settings, "langfuse_secret_key", "sk-lf-test-987654321")
        assert is_langfuse_enabled() is True

    def test_observability_status_payload(self):
        status = get_observability_status()
        assert status["provider"] == "Langfuse"
        assert "enabled" in status
        assert "configured" in status
        assert "features" in status
        assert len(status["features"]) >= 3

    def test_trace_url_safe_generation(self, monkeypatch):
        monkeypatch.setattr(settings, "enable_langfuse", True)
        monkeypatch.setattr(settings, "langfuse_public_key", "pk-lf-test-123456789")
        monkeypatch.setattr(settings, "langfuse_secret_key", "sk-lf-test-987654321")
        monkeypatch.setattr(settings, "langfuse_host", "https://cloud.langfuse.com")

        url = get_trace_url_safe("trace-abc-123")
        assert url is not None
        assert "trace-abc-123" in url
        assert "https://cloud.langfuse.com" in url

    def test_observability_status_endpoint(self, client):
        response = client.get("/api/observability/status")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "Langfuse"
        assert "configured" in data

