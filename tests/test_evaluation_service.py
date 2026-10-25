import json
from pathlib import Path
import pytest

from app.core.config import BASE_DIR
from app.services.evaluation import (
    EvalSample,
    calculate_keyword_coverage,
    extract_route_from_trace,
    evaluate_single_sample,
    get_mock_agent_response,
    load_evaluation_dataset,
    run_system_evaluation,
    save_evaluation_report,
)


class TestEvaluationMetrics:
    """
    Unit tests for evaluation service functions and metric calculations.
    """

    def test_calculate_keyword_coverage_perfect(self):
        keywords = ["NovaSecure", "VPN", "MFA"]
        text = "Please open NovaSecure VPN client and complete MFA."
        score, matched, missing = calculate_keyword_coverage(keywords, text)

        assert score == 1.0
        assert len(matched) == 3
        assert len(missing) == 0

    def test_calculate_keyword_coverage_partial(self):
        keywords = ["NovaSecure", "VPN", "Firewall", "Screenshot"]
        text = "NovaSecure VPN client failed to connect."
        score, matched, missing = calculate_keyword_coverage(keywords, text)

        assert score == 0.5
        assert set(matched) == {"NovaSecure", "VPN"}
        assert set(missing) == {"Firewall", "Screenshot"}

    def test_calculate_keyword_coverage_empty(self):
        score, matched, missing = calculate_keyword_coverage([], "Any text here")
        assert score == 1.0
        assert matched == []
        assert missing == []

        score_none, _, _ = calculate_keyword_coverage(["VPN"], "")
        assert score_none == 0.0

    def test_extract_route_from_trace(self):
        trace_direct = ["Incoming query", "Router → DIRECT", "Direct answer"]
        assert extract_route_from_trace(trace_direct) == "direct"

        trace_kb = ["Incoming query", "Router → KB", "Private KB retrieval"]
        assert extract_route_from_trace(trace_kb) == "kb"

        trace_fallback = ["Empty trace"]
        assert extract_route_from_trace(trace_fallback) == "kb"


class TestSampleEvaluation:
    """
    Tests evaluation of individual samples against ground truth.
    """

    @pytest.fixture
    def vpn_sample(self):
        return EvalSample(
            id="test-vpn-01",
            category="VPN Access",
            question="How do I connect to VPN?",
            expected_route="kb",
            expected_source="private_kb",
            ground_truth_keywords=["NovaSecure", "VPN", "MFA"],
            ground_truth_answer="Use NovaSecure VPN with MFA."
        )

    def test_evaluate_sample_pass(self, vpn_sample):
        response = {
            "answer": "Install NovaSecure VPN client and authenticate using MFA.",
            "source_used": "private_kb",
            "trace": ["Router → KB", "Private KB retrieval", "Answer generation → PRIVATE KB"]
        }
        result = evaluate_single_sample(vpn_sample, response, latency_seconds=0.15)

        assert result.passed is True
        assert result.route_match is True
        assert result.source_match is True
        assert result.keyword_coverage == 1.0
        assert result.latency_seconds == 0.15
        assert result.notes == "Pass"

    def test_evaluate_sample_route_mismatch(self, vpn_sample):
        response = {
            "answer": "Hello, how can I help you?",
            "source_used": "direct",
            "trace": ["Router → DIRECT", "Direct response"]
        }
        result = evaluate_single_sample(vpn_sample, response)

        assert result.passed is False
        assert result.route_match is False
        assert "Route mismatch" in result.notes

    def test_evaluate_sample_low_keyword_coverage(self, vpn_sample):
        response = {
            "answer": "You can connect using the network settings.",
            "source_used": "private_kb",
            "trace": ["Router → KB", "Private KB retrieval"]
        }
        # Keywords are NovaSecure, VPN, MFA. None are in response, so coverage is 0.0
        result = evaluate_single_sample(vpn_sample, response, min_keyword_threshold=0.5)

        assert result.passed is False
        assert result.keyword_coverage == 0.0
        assert "Low keyword coverage" in result.notes


class TestSystemEvaluationRunner:
    """
    Tests running system-level evaluation.
    """

    def test_run_system_evaluation_mock_mode(self):
        report = run_system_evaluation(use_mock=True)

        assert report.total_samples >= 5
        assert report.mode == "mock"
        assert report.routing_accuracy >= 0.8
        assert report.overall_pass_rate >= 0.8
        assert report.avg_latency_seconds >= 0.0
        assert len(report.category_metrics) >= 3

        # Every sample in results should have valid fields
        for res in report.results:
            assert res.sample_id
            assert res.actual_answer

    def test_save_and_verify_report_file(self, tmp_path):
        report = run_system_evaluation(use_mock=True)
        report_path = tmp_path / "test_report.json"

        save_evaluation_report(report, report_path)
        assert report_path.exists()

        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["total_samples"] == report.total_samples
        assert data["routing_accuracy"] == report.routing_accuracy
        assert "category_metrics" in data
