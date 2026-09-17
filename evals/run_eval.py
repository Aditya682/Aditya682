"""Regression eval runner - "rather than vibes-based testing."

For each example in golden_dataset.jsonl: runs the graph end-to-end
(auto-approving at the HITL gate, since this measures itinerary generation
quality, not the approval UX), checks the checkable predicates, runs the
LLM-as-judge on the subjective dimensions, and pulls step-count/latency
from the trace file that run wrote. Writes a timestamped JSON report and
diffs it against the previous run so a prompt/model change that silently
breaks a previously-passing example is visible immediately, not discovered
later.

Usage:
    python -m evals.run_eval
"""

from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from evals.judge import judge_itinerary
from evals.predicates import evaluate_example
from travel_agent.cli import run_trip_request
from travel_agent.config import ROOT_DIR, TRACE_DIR

load_dotenv()

GOLDEN_PATH = Path(__file__).parent / "golden_dataset.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def _load_golden() -> list[dict]:
    with GOLDEN_PATH.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def _trace_stats(session_id: str) -> dict:
    path = TRACE_DIR / f"{session_id}.jsonl"
    if not path.exists():
        return {"step_count": None, "total_duration_s": None}
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    finished = [e for e in events if e["event"] == "node_finished"]
    return {
        "step_count": max((e["step"] for e in events), default=0),
        "total_duration_s": round(sum(e["duration_s"] for e in finished), 3),
    }


def run_all() -> dict:
    examples = _load_golden()
    results = []

    for example in examples:
        print(f"[{example['id']}] running...", file=sys.stderr)
        outcome = run_trip_request(example["raw_query"], auto_approve=True)
        final_state = outcome["final_state"]

        predicate_result = evaluate_example(example, final_state)
        trace_stats = _trace_stats(outcome["session_id"])

        judge_result = None
        itinerary = final_state.get("itinerary")
        if itinerary is not None:
            score = judge_itinerary(example["raw_query"], itinerary)
            judge_result = score.model_dump()

        results.append(
            {
                "id": example["id"],
                "session_id": outcome["session_id"],
                "predicate_passed": predicate_result["passed"],
                "predicate_checks": predicate_result["checks"],
                "judge": judge_result,
                "trace": trace_stats,
            }
        )
        status = "PASS" if predicate_result["passed"] else "FAIL"
        print(f"[{example['id']}] {status}", file=sys.stderr)

    report = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "n_examples": len(examples),
        "n_passed": sum(1 for r in results if r["predicate_passed"]),
        "pass_rate": round(sum(1 for r in results if r["predicate_passed"]) / len(results), 3),
        "avg_step_count": _safe_mean([r["trace"]["step_count"] for r in results if r["trace"]["step_count"] is not None]),
        "avg_duration_s": _safe_mean([r["trace"]["total_duration_s"] for r in results if r["trace"]["total_duration_s"] is not None]),
        "avg_coherence_score": _safe_mean([r["judge"]["coherence_score"] for r in results if r["judge"]]),
        "avg_preference_fit_score": _safe_mean([r["judge"]["preference_fit_score"] for r in results if r["judge"]]),
        "results": results,
    }
    return report


def _safe_mean(values: list[float]) -> float | None:
    return round(statistics.mean(values), 3) if values else None


def _previous_report() -> dict | None:
    reports = sorted(RESULTS_DIR.glob("*.json"))
    if not reports:
        return None
    return json.loads(reports[-1].read_text())


def _print_regressions(previous: dict, current: dict) -> None:
    prev_by_id = {r["id"]: r["predicate_passed"] for r in previous["results"]}
    regressions = [
        r["id"] for r in current["results"] if prev_by_id.get(r["id"]) is True and r["predicate_passed"] is False
    ]
    fixes = [r["id"] for r in current["results"] if prev_by_id.get(r["id"]) is False and r["predicate_passed"] is True]
    if regressions:
        print(f"\nREGRESSIONS vs previous run: {regressions}", file=sys.stderr)
    if fixes:
        print(f"Fixed vs previous run: {fixes}", file=sys.stderr)
    if not regressions and not fixes:
        print("\nNo change in per-example pass/fail vs previous run.", file=sys.stderr)


def main() -> None:
    previous = _previous_report()
    report = run_all()

    out_path = RESULTS_DIR / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(report, indent=2, default=str))

    print("\n" + "=" * 60)
    print(f"Pass rate: {report['n_passed']}/{report['n_examples']} ({report['pass_rate']:.0%})")
    print(f"Avg steps/session: {report['avg_step_count']} | Avg duration/session: {report['avg_duration_s']}s")
    print(f"Avg judge scores - coherence: {report['avg_coherence_score']} | preference fit: {report['avg_preference_fit_score']}")
    print("=" * 60)

    if previous:
        _print_regressions(previous, report)

    print(f"\nFull report: {out_path.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()
