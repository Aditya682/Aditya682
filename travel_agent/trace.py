"""Observability: every graph node emits a structured JSONL event.

This is intentionally the simplest thing that gives real signal - no
tracing vendor dependency. Each session writes one file to traces/, and
evals/run_eval.py reads these files back to compute step-count and latency
metrics for the trajectory/convergence eval. Swapping in LangSmith/Langfuse
later means adding a second sink here, not restructuring how nodes report.
"""

from __future__ import annotations

import functools
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from travel_agent.config import TRACE_DIR


class Tracer:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.path = TRACE_DIR / f"{session_id}.jsonl"
        self.step_count = 0

    def log(self, event: str, **fields) -> None:
        record = {
            "session_id": self.session_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **fields,
        }
        with self.path.open("a") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def node_started(self, node: str) -> None:
        self.step_count += 1
        self.log("node_started", node=node, step=self.step_count)

    def node_finished(self, node: str, duration_s: float, summary: dict) -> None:
        self.log("node_finished", node=node, step=self.step_count, duration_s=round(duration_s, 3), summary=summary)


def traced(node_name: str):
    """Decorator for LangGraph node functions: state -> dict, tracer read from state["_tracer"]."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(state):
            tracer: Tracer | None = state.get("_tracer")
            start = time.perf_counter()
            if tracer:
                tracer.node_started(node_name)
            result = fn(state)
            duration = time.perf_counter() - start
            if tracer:
                summary = {k: v for k, v in (result or {}).items() if not k.startswith("_")}
                tracer.node_finished(node_name, duration, _shallow_summary(summary))
            return result

        return wrapper

    return decorator


def _shallow_summary(d: dict, max_len: int = 200) -> dict:
    out = {}
    for k, v in d.items():
        s = str(v)
        out[k] = s if len(s) <= max_len else s[:max_len] + "..."
    return out
