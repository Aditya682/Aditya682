# Agentic Goa Trip Planner

A production-shaped (not toy-shaped) agentic system, built as a portfolio
piece to demonstrate hands-on depth across multi-agent orchestration, tool
use, RAG, structured outputs, guardrails, human-in-the-loop, observability
and evaluation - the exact surface area covered by AI Product Manager /
technical PM interviews that probe agent systems rather than chatbot demos.

**The scenario:** a user says *"Plan a 5-day Goa trip for 2 people under
₹50,000. We prefer a beach hotel, want one day of sightseeing, and flexible
cancellation. Compare options and recommend the best itinerary."* The system
researches, evaluates options against real constraints, composes an
itinerary, and asks for explicit approval before the one action that would
actually commit money (a booking hold).

The travel domain is incidental. The point of the project is everything
underneath it.

## What's actually built

| Requirement | Where | Notes |
|---|---|---|
| Multi-agent orchestration | `travel_agent/graph.py` | Real [LangGraph](https://github.com/langchain-ai/langgraph) `StateGraph` - not a hand-rolled loop. Parser → parallel hotel/activity research → constraint check → itinerary composer → approval gate → booking. |
| Tool use | `travel_agent/agents/hotel_agent.py`, `activity_agent.py` | Anthropic's `tool_runner` + `@beta_tool`. The agent decides search filters; a tool call actually executes against the mock inventory. |
| RAG | `travel_agent/rag.py`, `travel_agent/data/knowledge_base/` | Deliberately dependency-free retrieval over a small corpus (area guide, cancellation policy notes, planning tips) - see the docstring for why, and what a real vector-DB swap-in looks like. |
| Memory | LangGraph checkpointer (`MemorySaver`) | Session state persists across the approval-gate pause/resume. |
| Structured outputs | `travel_agent/schemas.py` + `client.messages.parse` | Every LLM output that downstream code consumes is Pydantic-schema-constrained, not parsed from free text. |
| Guardrails | `travel_agent/tools/constraint_check.py` | Budget/preference compliance is checked in plain deterministic Python, not by asking an LLM if a number looks okay. Hotel selection is also anti-hallucination-guarded: the model picks from a JSON-schema `enum` of names actually returned by the tool call, so it can't invent a hotel. |
| Human-in-the-loop | `travel_agent/agents/approval.py` | LangGraph's native `interrupt()` / `Command(resume=...)` - the graph genuinely pauses; nothing past this node runs without an explicit approval. |
| Observability | `travel_agent/trace.py` | Every node emits structured JSONL trace events (step count, duration, output summary) to `traces/`. |
| Evaluation + LLM-as-judge | `evals/` | Golden dataset + checkable predicates (facts) + LLM-as-judge (subjective quality, on a cheaper model) + a regression runner that diffs against the previous run. |
| Experimentation | `travel_agent/config.py` | Model choice per role (agent vs. judge) is one env var, specifically so A/B-ing a model/prompt change against the eval harness is a one-line change. |
| MCP integration | `mcp_server/server.py` | The same tools the in-process agents use, exposed as an MCP server any MCP client (Claude Desktop, another agent) can call directly. |
| Monitoring | `evals/run_eval.py` | Regression report includes step-count/latency trends across runs - the offline half of "monitoring"; a real deployment would feed the same trace events to a dashboard instead of a JSON file. |

## Architecture

```
                        START
                          |
                    parse_request            (planner: NL -> TripRequest, structured output)
                     /          \
        research_hotels      research_activities      (parallel, tool_runner + tool use)
                     \          /
                  check_constraints                    (deterministic guardrail, no LLM)
                    /          \
     [fail, retries left]   [pass]
     research_hotels(loop)   compose_itinerary          (structured output, facts injected not generated)
                                   |
                             approval_gate               (interrupt() - human-in-the-loop)
                              /        \
                       [approved]   [rejected]
                          book         end
                           |
                          END
```

The retry loop only re-runs `research_hotels`, not `research_activities` -
this was verified against the installed LangGraph version (not assumed):
a node with two incoming edges fans in once per superstep, and a selective
retry to only one predecessor still fires the fan-in node once, reading the
other branch's last-known state. See the test in the project history if you
want to reproduce it.

## Design decisions worth defending in an interview

- **Constraint checking is plain Python, not an LLM call.** The JD language
  is "evaluates constraints" - that should be a deterministic numeric
  check (is 41,700 ≤ 50,000?), not a model's judgment call. The LLM decides
  *what* to propose; a guardrail function decides whether it's *allowed*.
- **Hotel/activity selection uses JSON-schema `enum` constraints over the
  actual tool results**, not free-text picks trusted at face value. This is
  a directly testable anti-hallucination guardrail, not a prompt asking the
  model nicely not to invent a hotel.
- **The itinerary composer never re-generates factual data.** Hotel name,
  price, and budget numbers come straight from the tool-backed steps; the
  LLM is only asked for the genuinely generative part (day sequencing and
  rationale), narrowly schema-constrained.
- **The eval judge runs on Haiku 4.5, generation runs on Sonnet 5.** Grading
  a structured itinerary against a rubric doesn't need frontier-model
  reasoning; spending Opus-tier tokens on it would be the "measure cost per
  request, not per completed task" mistake.
- **RAG is a from-scratch BM25-lite scorer, not a vector DB**, because the
  corpus is three markdown files - a vector index would add a dependency
  without adding retrieval quality. The interface is the real contract;
  swapping in Milvus/pgvector later touches one file.

## What's a known simplification (roadmap, not hidden)

- Mock hotel/activity inventory (`travel_agent/data/*.json`), not a live
  API - the point of this project is the agent architecture, not becoming a
  travel API integrator. Swapping in a real provider means rewriting
  `tools/hotel_search.py`'s body; every caller (agent, MCP server, eval
  harness) is unaffected.
- No flight search - scope was kept to hotel + sightseeing to keep the
  first working version tight; flights would be a third research agent
  following the exact same tool-use pattern.
- The eval harness auto-approves at the HITL gate so it can run
  unattended - it's measuring itinerary generation quality, not the
  approval UX.
- Session memory is per-conversation (LangGraph checkpointer), not
  cross-session user preference memory.

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY

python -m travel_agent.cli "Plan a 5-day Goa trip for 2 people under INR 50000. We prefer a beach hotel, want one day of sightseeing, and flexible cancellation."
```

This prints the proposed itinerary, prompts for approval on the terminal,
and (if approved) prints a mock booking confirmation. A trace file lands in
`traces/<session_id>.jsonl`.

### Running the eval suite

```bash
python -m evals.run_eval
```

Runs all 10 golden-dataset examples end-to-end, checks predicates, scores
each with the LLM judge, and writes a timestamped report to
`evals/results/`. Run it twice in a row after any prompt/model change to
see the regression diff against the previous run.

### Running the MCP server

```bash
python -m mcp_server.server
```

Point an MCP-compatible client (e.g. Claude Desktop's config) at this
module over stdio to drive `find_hotels`, `find_activities`,
`check_trip_budget` and `goa_area_guide` directly.

## What hasn't been live-tested yet

Everything that doesn't require an API call (tools, constraint math, RAG
retrieval, the LangGraph topology and its fan-out/fan-in/retry behavior,
the MCP server's tool registration and a full `check_trip_budget` call) has
been run and verified in this environment. The LLM-driven nodes
(`parse_request`, `research_hotels`, `research_activities`,
`compose_itinerary`, the eval judge) are written against verified current
SDK signatures (`client.messages.parse`, `tool_runner`, `@beta_tool`,
`output_config.format`) but need a real `ANTHROPIC_API_KEY` to exercise -
no key was available in the build environment. Run the CLI command above
first; if anything breaks on a live call, it's the fastest way to find it.
