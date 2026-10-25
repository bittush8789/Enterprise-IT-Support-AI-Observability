import json
from pathlib import Path
import pytest
from langchain_core.documents import Document

from app.core.config import get_settings, BASE_DIR
from app.services.ingestion import load_file, chunk_documents, SUPPORTED
from app.services.evaluation import load_evaluation_dataset, EvalSample

settings = get_settings()


class TestSampleKBValidation:
    """
    Validates company knowledge base datasets and integrity.
    """

    def test_sample_kb_directory_exists(self):
        kb_dir = Path(settings.sample_kb_dir)
        assert kb_dir.exists(), f"Sample KB directory {kb_dir} does not exist"
        assert kb_dir.is_dir(), f"{kb_dir} is not a directory"

    def test_required_kb_files_exist(self):
        kb_dir = Path(settings.sample_kb_dir)
        handbook = kb_dir / "company_it_handbook.md"
        runbook = kb_dir / "service_desk_runbook.md"

        assert handbook.exists(), "company_it_handbook.md is missing from sample KB"
        assert runbook.exists(), "service_desk_runbook.md is missing from sample KB"

        assert handbook.stat().st_size > 200, "company_it_handbook.md appears too small or empty"
        assert runbook.stat().st_size > 200, "service_desk_runbook.md appears too small or empty"

    def test_handbook_contains_core_it_policies(self):
        handbook_path = Path(settings.sample_kb_dir) / "company_it_handbook.md"
        content = handbook_path.read_text(encoding="utf-8")

        required_sections = [
            "VPN Access",
            "Password Reset Policy",
            "Multi-Factor Authentication",
            "Software Installation",
            "Lost or Stolen Laptop",
        ]
        for section in required_sections:
            assert section in content, f"Required section '{section}' missing from handbook"

    def test_runbook_contains_core_procedures(self):
        runbook_path = Path(settings.sample_kb_dir) / "service_desk_runbook.md"
        content = runbook_path.read_text(encoding="utf-8")

        required_sections = [
            "Email Troubleshooting",
            "Laptop Performance",
            "Ticket Priority",
            "P1",
        ]
        for section in required_sections:
            assert section in content, f"Required section '{section}' missing from runbook"


class TestDocumentIngestionValidation:
    """
    Validates document loader and chunking pipeline.
    """

    def test_load_supported_file_types(self, tmp_path):
        # Markdown
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test Policy\nThis is a test document.", encoding="utf-8")
        docs = load_file(md_file)
        assert len(docs) == 1
        assert "Test Policy" in docs[0].page_content
        assert docs[0].metadata["source"] == str(md_file)

        # Plain text
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Plain text knowledge content.", encoding="utf-8")
        docs_txt = load_file(txt_file)
        assert len(docs_txt) == 1
        assert docs_txt[0].page_content == "Plain text knowledge content."

    def test_load_unsupported_file_raises_error(self, tmp_path):
        bad_file = tmp_path / "malicious.exe"
        bad_file.write_bytes(b"bad content")
        with pytest.raises(ValueError, match="Unsupported file type"):
            load_file(bad_file)

    def test_chunking_documents_properties(self):
        long_text = "Corporate IT policy statement. " * 100
        doc = Document(page_content=long_text, metadata={"source": "long_policy.md"})
        chunks = chunk_documents([doc])

        assert len(chunks) > 1, "Long document should be split into multiple chunks"
        for chunk in chunks:
            assert len(chunk.page_content) <= 1000, "Chunk exceeded maximum length expectation"
            assert chunk.metadata["source"] == "long_policy.md", "Metadata source was lost in chunking"
            assert "start_index" in chunk.metadata, "start_index should be added by splitter"


class TestEvaluationDatasetValidation:
    """
    Validates evaluation benchmark dataset structure, schema, and coverage.
    """

    def test_evaluation_dataset_file_exists(self):
        eval_path = BASE_DIR / "data" / "eval_dataset.json"
        assert eval_path.exists(), f"Evaluation dataset not found at {eval_path}"
        assert eval_path.stat().st_size > 0, "Evaluation dataset is empty"

    def test_evaluation_dataset_schema(self):
        samples = load_evaluation_dataset()
        assert len(samples) >= 5, "Evaluation dataset must contain at least 5 benchmark cases"

        valid_routes = {"kb", "direct"}
        valid_sources = {"private_kb", "web_search", "direct"}

        for s in samples:
            assert isinstance(s, EvalSample)
            assert s.id.strip(), "Sample ID cannot be empty"
            assert s.question.strip(), f"Sample {s.id} question is empty"
            assert s.expected_route in valid_routes, f"Sample {s.id} invalid route: {s.expected_route}"
            assert s.expected_source in valid_sources, f"Sample {s.id} invalid source: {s.expected_source}"
            assert len(s.ground_truth_keywords) > 0, f"Sample {s.id} must have at least one ground truth keyword"

    def test_dataset_coverage_has_both_kb_and_direct(self):
        samples = load_evaluation_dataset()
        routes = {s.expected_route for s in samples}
        sources = {s.expected_source for s in samples}

        assert "kb" in routes, "Evaluation dataset lacks 'kb' route test cases"
        assert "direct" in routes, "Evaluation dataset lacks 'direct' route test cases"
        assert "private_kb" in sources, "Evaluation dataset lacks 'private_kb' test cases"
        assert "direct" in sources, "Evaluation dataset lacks 'direct' conversational cases"
