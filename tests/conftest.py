import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from app.core.config import get_settings
from app.main import app
from app.services.audit import init_db

settings = get_settings()


@pytest.fixture(autouse=True)
def isolate_audit_db(tmp_path, monkeypatch):
    """
    Ensures every test runs against an isolated temporary SQLite database.
    """
    test_db = tmp_path / "test_audit.db"
    monkeypatch.setattr(settings, "audit_db_path", str(test_db))
    init_db()
    yield test_db


@pytest.fixture
def client():
    """
    FastAPI test client.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_documents():
    """
    Sample Document instances for ingestion and vectorstore tests.
    """
    return [
        Document(
            page_content="To connect to the corporate VPN, install the NovaSecure client and authenticate with MFA.",
            metadata={"source": "company_it_handbook.md", "category": "VPN"}
        ),
        Document(
            page_content="Company passwords must contain at least 14 characters. Never share your password or MFA code.",
            metadata={"source": "company_it_handbook.md", "category": "Password"}
        )
    ]


@pytest.fixture
def mock_agent_result():
    """
    Standard successful agent result structure.
    """
    return {
        "answer": "To connect to the VPN, install NovaSecure and authenticate using your MFA credentials.",
        "source_used": "private_kb",
        "trace": [
            "Router → KB",
            "Private KB retrieval → 2 chunks",
            "KB evidence grade → GOOD",
            "Answer generation → PRIVATE KB"
        ],
        "citations": [{"title": "company_it_handbook.md", "url": "", "type": "private_kb"}],
        "current_query": "How do I connect to VPN?",
    }
