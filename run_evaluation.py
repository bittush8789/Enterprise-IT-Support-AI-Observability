import argparse
import sys
from pathlib import Path
from app.services.evaluation import run_system_evaluation, save_evaluation_report


def print_banner():
    print("=" * 80)
    print("     Enterprise IT Support Agentic RAG Copilot - Evaluation Runner")
    print("=" * 80)


def print_report_summary(report, threshold: float):
    print("\n" + "-" * 80)
    print(f" Mode:                 {report.mode.upper()}")
    print(f" Timestamp:            {report.timestamp}")
    print(f" Total Samples:        {report.total_samples}")
    print(f" Routing Accuracy:     {report.routing_accuracy * 100:.1f}%")
    print(f" Source Accuracy:      {report.source_accuracy * 100:.1f}%")
    print(f" Avg Keyword Coverage: {report.avg_keyword_coverage * 100:.1f}%")
    print(f" Overall Pass Rate:    {report.overall_pass_rate * 100:.1f}%")
    print(f" Average Latency:      {report.avg_latency_seconds:.2f}s")
    print("-" * 80)

    print("\nDetailed Sample Results:")
    print(f"{'ID':<10} {'Category':<22} {'Expected':<12} {'Actual':<12} {'KW Match':<10} {'Status':<8}")
    print("-" * 80)
    for r in report.results:
        status_str = "PASS" if r.passed else "FAIL"
        kw_str = f"{r.keyword_coverage * 100:.0f}%"
        print(f"{r.sample_id:<10} {r.category[:20]:<22} {r.expected_source:<12} {r.actual_source:<12} {kw_str:<10} {status_str:<8}")

    print("\nCategory Performance:")
    print(f"{'Category':<28} {'Total':<8} {'Pass Rate':<12} {'Routing Acc':<12}")
    print("-" * 62)
    for cat, metrics in report.category_metrics.items():
        pass_pct = f"{metrics['pass_rate'] * 100:.1f}%"
        route_pct = f"{metrics['routing_accuracy'] * 100:.1f}%"
        print(f"{cat[:26]:<28} {int(metrics['total']):<8} {pass_pct:<12} {route_pct:<12}")

    print("-" * 80)
    passed = report.overall_pass_rate >= threshold
    if passed:
        print(f"RESULT: PASSED (Pass rate {report.overall_pass_rate * 100:.1f}% >= threshold {threshold * 100:.1f}%)")
    else:
        print(f"RESULT: FAILED (Pass rate {report.overall_pass_rate * 100:.1f}% < threshold {threshold * 100:.1f}%)")
    print("=" * 80)
    return passed


def main():
    parser = argparse.ArgumentParser(description="Run Evaluation on Agentic RAG Copilot")
    parser.add_argument("--mode", choices=["mock", "live"], default="mock", help="Evaluation mode (default: mock)")
    parser.add_argument("--dataset", type=str, default=None, help="Path to evaluation dataset JSON")
    parser.add_argument("--output", type=str, default="data/eval_report.json", help="Path to save evaluation report JSON")
    parser.add_argument("--threshold", type=float, default=0.8, help="Pass rate threshold (default: 0.8)")

    args = parser.parse_args()

    print_banner()
    print(f"Starting evaluation in {args.mode.upper()} mode...")
    use_mock = (args.mode == "mock")

    try:
        report = run_system_evaluation(
            dataset_path=args.dataset,
            use_mock=use_mock,
        )
        save_evaluation_report(report, args.output)
        print(f"\nEvaluation report saved to: {args.output}")

        passed = print_report_summary(report, args.threshold)
        sys.exit(0 if passed else 1)

    except Exception as exc:
        print(f"\nEvaluation execution failed with error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
