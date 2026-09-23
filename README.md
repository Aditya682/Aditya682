# Book with AI — a Goa trip-planning agent, built PM-first

A portfolio project with a deliberate constraint: **the product spec was
written and stress-tested before a single line of code**, using the same
discipline real Agentic AI PM roles (Navan's "Book with AI," Expedia's
Personal AI Agents / Agentic Search, MakeMyTrip's Myra) are actually hired
to apply. This repo documents that process end-to-end - every design
decision, every review round, and every real gap the review process
caught.

The scenario: a user says *"Plan a 5-day Goa trip for 2 people under
₹30,000. We prefer a beach hotel, want one day of sightseeing, and
flexible cancellation."* The system researches, adapts within bounded
autonomy, and asks for approval before any consequential action (a
booking). The travel domain is incidental - the point is the discipline
around **problem framing → eval design → architecture → build → launch →
iterate**, applied for real.

## Status

| Phase | Deliverable | Status |
|---|---|---|
| 0 | Problem discovery, autonomy boundary, guardrail seed | ✅ Done |
| 1 | One-pager (problem, user, why-agentic, value prop, metrics, scope) | ✅ Done |
| 2 | Eval-driven spec (golden dataset, trajectory, judge) | ✅ Done |
| 3 | Feasibility RFC (model, RAG, tools/MCP, orchestration) | ✅ Done |
| 4 | Build sprints (acceptance criteria + implementation) | 🔜 Next |
| 5 | Launch readiness (guardrail policy, monitoring requirements) | Not started |
| 6 | Eval-driven iteration backlog | Not started |

Phases 0-3 are pure product/architecture work - no code yet, by design.
Phase 4 is where this becomes a working system.

## Why this project exists

Most "I built an agent" portfolio pieces skip straight to code and
demonstrate vocabulary (RAG, MCP, LangGraph) without demonstrating the
actual job: deciding *whether* an agent is the right tool, defining what
"correct" means before building, and designing the guardrails that make
autonomy safe. This project inverts that - see
[`docs/agentic-pm-competency-map.md`](docs/agentic-pm-competency-map.md)
for the full reasoning and the real job postings (Navan, Expedia,
MakeMyTrip, Microsoft, LangChain) it's grounded against, and
[`docs/pm-playbook.md`](docs/pm-playbook.md) for the six-phase process
used to build it.

## What each phase actually decided

### Phase 0 — Is this even an agent problem?
[`docs/phase0-problem-discovery.md`](docs/phase0-problem-discovery.md)

Before any architecture: walked through why trip *composition* under
competing constraints is adaptive (not a fixed ranking over known
inventory), traced today's manual process to find that human judgment
sits specifically at trade-off resolution - not "everywhere" - and drew a
hard distinction between a wrong *recommendation* (low stakes, inspectable,
rejectable) and a wrong *booking* (external, financial, often
irreversible). That distinction produced the core design principle:

> Autonomy is granted to exploration, not to preference decisions or
> irreversible commitments.

Output: a decision-level (not stage-level) AUTO/ASK boundary table, a
bounded-retry policy (max 3 adaptation rounds, then surface alternatives
and ask), and the requirement that any booking-commitment value must come
from a trusted source, re-validated immediately before execution - never
asserted by the LLM.

### Phase 1 — One-pager
[`docs/phase1-one-pager.md`](docs/phase1-one-pager.md)

Problem, target user, why-agentic (inherited from Phase 0), value prop,
and out-of-scope. The success-metrics section went through real revision:
the first draft asserted targets (≥60% completion, <5 min) with no stated
basis - the fix was a 5-scenario manual baseline method, a split between
system-processing-time and wall-clock-time (so a slow human response to
an ASK doesn't make the system look slow), and a precise definition of
"eligible session" so the completion-rate metric is actually computable
without ambiguity.

### Phase 2 — Eval-driven spec
[`docs/phase2-eval-spec.md`](docs/phase2-eval-spec.md)

The real PRD for a probabilistic system: a 20-case golden dataset (split
15 core-regression / 5 calibration-holdout, to avoid tuning the judge on
the exact cases it will grade forever), a trajectory spec that catches a
run reaching a *valid* itinerary through an *illegal* path (e.g. an
unnecessary ASK, or a parameter change beyond policy), and a 5-dimension
LLM-judge rubric with an explicit human-calibration procedure (two
independent raters, ≥90% agreement target, a decision tree for whether a
disagreement means the judge is wrong, the rubric is ambiguous, or the
judge has systematic bias).

### Phase 3 — Feasibility RFC
[`docs/phase3-feasibility-rfc.md`](docs/phase3-feasibility-rfc.md)

Translates Phases 0-2 into buildable requirements: per-role model
selection (agent vs. judge, independently versioned so a judge upgrade
can't silently shift the regression suite), a RAG design that keeps
dynamic transactional data (price, availability) out of the retrieval
layer entirely, a tool inventory where `book_trip` independently validates
an approval token's freshness/session/parameters rather than trusting
correct call ordering elsewhere in the system, and a single-agent state
machine with four separately-bounded counters
(`adaptation_round_count`, `replan_count`, `booking_revalidation_count`,
`tool_retry_count`) so every autonomous loop in the system - not just the
first one - has an explicit stopping condition.

**The one architectural principle threaded through all four phases:**
*the agent proposes what it wants to do; the orchestrator and tools decide
whether it's allowed to.* Nothing in this system trusts the model's own
account of what it did or what was approved.

## Real gaps this process caught

Worth naming explicitly, because it's the actual evidence the process
works rather than being theater: an earlier reference implementation of
this same project (built in a prior session, since discarded so the build
could be done hands-on) was missing three things the PM review surfaced
independently - inventory snapshot versioning for reproducible evals,
trajectory-level pass/fail in the eval harness (it only checked final
output), and pre-booking re-validation against live inventory before
executing a booking. All three are now explicit requirements in Phases 2
and 3 before any code exists.

## Repository layout

```
docs/
  agentic-pm-competency-map.md   Reference: the full AI PM competency map,
                                  grounded in real job postings
  pm-playbook.md                 The 6-phase process used on this project
  phase0-problem-discovery.md    Is this an agent problem? Autonomy boundary.
  phase1-one-pager.md            Problem, user, value prop, metrics, scope
  phase2-eval-spec.md            Golden dataset, trajectory spec, judge rubric
  phase3-feasibility-rfc.md      Model/RAG/tools/orchestration architecture
```

Phase 4 onward will add `travel_agent/` (the implementation),
`mcp_server/` (tool exposure over MCP), and `evals/` (the golden dataset
and regression runner specified in Phase 2) - built against these specs,
not the other way around.

## Setup (for Phase 4 onward)

```bash
python -m venv .venv && source .venv/bin/activate
pip install anthropic python-dotenv   # more deps land as Phase 4 progresses
cp .env.example .env   # add ANTHROPIC_API_KEY
```
