import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.config import get_settings, BASE_DIR

logger = logging.getLogger(__name__)
settings = get_settings()

DEFAULT_DATASET_PATH = BASE_DIR / "data" / "eval_dataset.json"



class EvalSample(BaseModel):
    id: str
    category: str
    question: str
    expected_route: str = Field(description="Expected router decision: 'kb' or 'direct'")
    expected_source: str = Field(description="Expected final source: 'private_kb', 'web_search', or 'direct'")
    ground_truth_keywords: List[str] = Field(default_factory=list)
    ground_truth_answer: str = ""


class SampleEvalResult(BaseModel):
    sample_id: str
    category: str
    question: str
    expected_route: str
    actual_route: str
    route_match: bool
    expected_source: str
    actual_source: str
    source_match: bool
    keyword_coverage: float
    matched_keywords: List[str]
    missing_keywords: List[str]
    latency_seconds: float
    actual_answer: str
    passed: bool
    notes: str = ""


class EvaluationReport(BaseModel):
    timestamp: str
    mode: str
    total_samples: int
    routing_accuracy: float
    source_accuracy: float
    avg_keyword_coverage: float
    overall_pass_rate: float
    avg_latency_seconds: float
    category_metrics: Dict[str, Dict[str, float]]
    results: List[SampleEvalResult]


def load_evaluation_dataset(dataset_path: Optional[Path | str] = None) -> List[EvalSample]:
    path = Path(dataset_path) if dataset_path else DEFAULT_DATASET_PATH
    if not path.is_file():
        raise FileNotFoundError(f"Evaluation dataset not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Evaluation dataset must be a JSON array of test cases.")

    samples = [EvalSample(**item) for item in data]
    return samples


def calculate_keyword_coverage(expected_keywords: List[str], text: str) -> tuple[float, List[str], List[str]]:
    if not expected_keywords:
        return 1.0, [], []

    # Normalize hyphens and quotation marks for robust text matching
    lower_text = (text or "").lower().replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    matched = []
    missing = []

    for kw in expected_keywords:
        kw_clean = kw.strip().lower().replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
        if kw_clean in lower_text:
            matched.append(kw)
        else:
            missing.append(kw)

    score = round(len(matched) / len(expected_keywords), 3)
    return score, matched, missing



def get_mock_agent_response(sample: EvalSample) -> Dict[str, Any]:
    """
    Deterministic mock response for offline evaluation and unit tests.
    """
    q_lower = sample.question.lower()
    if sample.expected_route == "direct":
        if "thank" in q_lower:
            ans = "You are very welcome! I am glad I could help. Feel free to reach out anytime if you need further IT assistance."
        else:
            ans = "Hello! I am your NovaRetail IT Support Copilot. How can I assist you with your IT needs today?"
        return {
            "answer": ans,
            "source_used": "direct",
            "trace": ["Router → DIRECT", "Direct response → no retrieval"],
            "citations": [],
            "current_query": sample.question,
        }

    elif sample.expected_source == "web_search":
        return {
            "answer": f"According to current external vendor status, Microsoft Teams outage guidance recommends checking the Microsoft 365 admin center for live incident updates.",
            "source_used": "web_search",
            "trace": ["Router → KB", "Private KB retrieval → 0 chunks", "KB evidence grade → WEAK", "Web fallback → Tavily search", "Web evidence grade → GOOD", "Answer generation → WEB SEARCH"],
            "citations": [{"title": "Microsoft Status", "url": "https://status.office.com", "type": "web"}],
            "current_query": sample.question,
        }
    else:
        # Private KB response based on sample ground truth
        return {
            "answer": f"Based on the company IT handbook, {sample.ground_truth_answer}",
            "source_used": "private_kb",
            "trace": ["Router → KB", "Private KB retrieval → 3 chunks", "KB evidence grade → GOOD", "Answer generation → PRIVATE KB"],
            "citations": [{"title": "company_it_handbook.md", "url": "", "type": "private_kb"}],
            "current_query": sample.question,
        }


def extract_route_from_trace(trace: List[str]) -> str:
    for step in trace:
        step_upper = step.upper()
        if "ROUTER → DIRECT" in step_upper:
            return "direct"
        if "ROUTER → KB" in step_upper:
            return "kb"
    return "kb"


def evaluate_single_sample(
    sample: EvalSample,
    response: Dict[str, Any],
    latency_seconds: float = 0.0,
    min_keyword_threshold: float = 0.5,
) -> SampleEvalResult:
    trace = response.get("trace", [])
    actual_source = response.get("source_used", "unknown")
    actual_answer = response.get("answer", "")

    actual_route = extract_route_from_trace(trace)
    if actual_source == "direct":
        actual_route = "direct"

    route_match = (actual_route.lower() == sample.expected_route.lower())
    source_match = (actual_source.lower() == sample.expected_source.lower())

    kw_score, matched_kws, missing_kws = calculate_keyword_coverage(
        sample.ground_truth_keywords, actual_answer
    )

    kw_pass = (kw_score >= min_keyword_threshold) if sample.ground_truth_keywords else True
    passed = route_match and source_match and kw_pass

    notes = []
    if not route_match:
        notes.append(f"Route mismatch: expected {sample.expected_route}, got {actual_route}")
    if not source_match:
        notes.append(f"Source mismatch: expected {sample.expected_source}, got {actual_source}")
    if not kw_pass:
        notes.append(f"Low keyword coverage: {kw_score * 100:.1f}%")


    return SampleEvalResult(
        sample_id=sample.id,
        category=sample.category,
        question=sample.question,
        expected_route=sample.expected_route,
        actual_route=actual_route,
        route_match=route_match,
        expected_source=sample.expected_source,
        actual_source=actual_source,
        source_match=source_match,
        keyword_coverage=kw_score,
        matched_keywords=matched_kws,
        missing_keywords=missing_kws,
        latency_seconds=round(latency_seconds, 3),
        actual_answer=actual_answer,
        passed=passed,
        notes="; ".join(notes) if notes else "Pass",
    )


def run_system_evaluation(
    dataset_path: Optional[Path | str] = None,
    ask_runner: Optional[Callable[[str], Dict[str, Any]]] = None,
    use_mock: bool = False,
    min_keyword_threshold: float = 0.5,
) -> EvaluationReport:
    samples = load_evaluation_dataset(dataset_path)

    if not use_mock and ask_runner is None:
        from app.rag.workflow import ask
        ask_runner = ask

    results: List[SampleEvalResult] = []
    total_time = 0.0

    for sample in samples:
        t0 = time.perf_counter()
        if use_mock:
            response = get_mock_agent_response(sample)
        else:
            try:
                response = ask_runner(sample.question)
            except Exception as e:
                logger.error(f"Error querying agent for sample {sample.id}: {e}")
                response = {
                    "answer": f"Error: {e}",
                    "source_used": "error",
                    "trace": ["Execution error occurred"],
                    "citations": [],
                }
        t1 = time.perf_counter()
        elapsed = t1 - t0
        total_time += elapsed

        result = evaluate_single_sample(
            sample=sample,
            response=response,
            latency_seconds=elapsed,
            min_keyword_threshold=min_keyword_threshold,
        )
        results.append(result)

    total = len(results)
    if total == 0:
        raise ValueError("No evaluation samples were processed.")

    route_correct_count = sum(1 for r in results if r.route_match)
    source_correct_count = sum(1 for r in results if r.source_match)
    passed_count = sum(1 for r in results if r.passed)
    avg_kw_coverage = sum(r.keyword_coverage for r in results) / total
    avg_latency = total_time / total

    # Per-category metrics
    categories = sorted(list({r.category for r in results}))
    category_metrics: Dict[str, Dict[str, float]] = {}
    for cat in categories:
        cat_results = [r for r in results if r.category == cat]
        cat_total = len(cat_results)
        category_metrics[cat] = {
            "total": float(cat_total),
            "pass_rate": round(sum(1 for r in cat_results if r.passed) / cat_total, 3),
            "routing_accuracy": round(sum(1 for r in cat_results if r.route_match) / cat_total, 3),
            "avg_keyword_coverage": round(sum(r.keyword_coverage for r in cat_results) / cat_total, 3),
        }

    return EvaluationReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        mode="mock" if use_mock else "live",
        total_samples=total,
        routing_accuracy=round(route_correct_count / total, 3),
        source_accuracy=round(source_correct_count / total, 3),
        avg_keyword_coverage=round(avg_kw_coverage, 3),
        overall_pass_rate=round(passed_count / total, 3),
        avg_latency_seconds=round(avg_latency, 3),
        category_metrics=category_metrics,
        results=results,
    )


def save_evaluation_report(report: EvaluationReport, output_path: Path | str) -> None:
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2)
