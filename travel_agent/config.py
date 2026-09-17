"""Central config. Every model choice is env-overridable so cost/quality
tradeoffs are a config change, not a code change.

Default split (deliberate, not arbitrary):
- AGENT_MODEL (Sonnet 5): the research/composer agents. Structured,
  tool-calling work that doesn't need frontier reasoning.
- JUDGE_MODEL (Haiku 4.5): the eval judge. Grading a structured itinerary
  against a rubric is a cheap task; spending Opus-tier tokens on it would
  be the "measure cost per completed task" mistake, not a saving.
Bump either to claude-opus-5 via env vars if quality, not cost, becomes
the binding constraint.
"""

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"
TRACE_DIR = ROOT_DIR / "traces"
TRACE_DIR.mkdir(exist_ok=True)

AGENT_MODEL = os.environ.get("CLAUDE_AGENT_MODEL", "claude-sonnet-5")
JUDGE_MODEL = os.environ.get("CLAUDE_JUDGE_MODEL", "claude-haiku-4-5")

MAX_RESEARCH_RETRIES = int(os.environ.get("MAX_RESEARCH_RETRIES", "2"))
