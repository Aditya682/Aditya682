# Phase 3: Feasibility RFC - Book with AI

The handoff point from "PM decides" to "engineering builds." Translates
Phases 0-2 into system requirements. The central architectural principle
threaded through every section: **the agent proposes what it wants to do;
the orchestrator and tools decide whether it's allowed to** - reasoning is
never trusted as its own enforcement.

## 1. Model selection

The agent and the judge (Phase 2) are not the same model choice - they
optimize for different things.

| Criterion | Agent / Composition | Judge |
|---|---|---|
| Reasoning quality | High | Medium-High |
| Latency | High importance | Medium |
| Cost | High importance | High |
| Context window | High | Medium |
| Tool calling | Critical | Not required |
| Structured output | Critical | High |
| Determinism/consistency | High | Very high |
| Creativity | Useful | Low |
| External actions | Required | None |

**Agent model:** must interpret constraints, select tools, extract tool
parameters, classify failures, decide AUTO vs. ASK, compose alternatives,
respect the retry budget, and produce structured state transitions.
Benchmark at least two candidates rather than hard-coding a vendor/model
choice - acceptance test is the Phase 2 20-case golden dataset, scoring
trajectory correctness + deterministic predicates + latency + token/cost
per session + tool-call correctness + structured-output validity. The
winner is best quality *subject to* acceptable latency and cost, not
highest quality unconditionally.

**Judge model:** doesn't need tool-calling capability - receives request +
observed outcome + evidence + agent response + applicable rubric, returns
structured scores. Prefer a smaller/cheaper model that demonstrates high
human agreement over defaulting to the largest model. Versioned
independently: `judge_model_version`, `judge_prompt_version`,
`rubric_version` - otherwise a judge-model upgrade can make yesterday's
regression suite appear to shift without the product actually changing.

**Product requirement:** model/prompt selection is itself an evaluated
configuration - `agent_model`, `judge_model`, `agent_prompt`,
`judge_prompt` must each be independently changeable and rerunnable
against the frozen golden dataset.

## 2. Context / RAG design

RAG is never authoritative for dynamic transactional data - that always
comes from live trusted tools, never a knowledge-base retrieval layer.

| Data type | Examples | Source |
|---|---|---|
| Dynamic/transactional | availability, current price, room inventory, activity availability, cancellation terms, booking status | Live trusted tools only |
| Stable/semi-stable | area/location guides, beach characteristics, activity descriptions & suitability, hotel/property descriptions, cancellation-policy explanations, travel guidance, product policy/autonomy rules | RAG corpus |

Initial corpus stays trusted and relevant, not an arbitrary travel-blog
ingestion. Each document carries `source`, `document_id`, `version`,
`updated_at`, `effective_from`, `expires_at`; retrieval rejects or
deprioritizes expired content.

**Retrieval flow:** the request is first routed - "does this require Goa
knowledge?" A question like "what's available on October 12" or "what's
the current price" goes straight to the inventory tool, never to RAG.

**Empty retrieval:** the agent must distinguish "no knowledge retrieved"
from "can still answer via trusted tool/data" - if neither applies, it
says so explicitly ("I don't have enough verified information about that
activity to recommend it") rather than manufacturing Goa-specific facts.
This is an explicit case type in the golden dataset (ties to Phase 2's
`REFUSAL`/groundedness handling).

## 3. Tools / MCP design

The tool layer enforces permissions; the prompt does not.

| Tool | Inputs | Outputs | Type | Permission |
|---|---|---|---|---|
| `search_hotels` | dates, guests, budget, location/filter | hotel options + availability + price + policies | Read-only | AUTO |
| `search_activities` | dates, category, travelers, budget/location | activity options + availability + price | Read-only | AUTO |
| `get_hotel_details` | hotel ID | structured property details | Read-only | AUTO |
| `get_activity_details` | activity ID | structured activity details | Read-only | AUTO |
| `check_inventory` | hotel/activity ID + dates/guests | current availability + price | Read-only | AUTO |
| `compose_trip` | hotel + activities + constraints | deterministic total + conflicts | Read-only | AUTO |
| `retrieve_goa_knowledge` | query + filters | versioned knowledge chunks | Read-only | AUTO |
| `validate_trip` | proposed trip + constraints | predicate results | Read-only | AUTO |
| `create_booking_preview` | approved trip | booking summary + current price/policy | Read-only | GATE |
| `book_trip` | validated booking preview + approval token | booking confirmation | Mutating | GATE |
| `cancel_booking` | booking ID + explicit cancellation approval | cancellation result | Mutating | GATE |

**Preview vs. booking are deliberately separate tools.** The agent can
prepare a current preview but cannot convert it into a transaction merely
by having generated one - `book_trip` independently rejects calls without
a valid approval token, so a hallucinating agent (or a prompt injection)
asserting "the user already confirmed" cannot bypass the gate; the tool
layer never trusts the model's claim.

**`book_trip`'s independent validation** (defense in depth - the
orchestrator's call ordering is useful but is not the security boundary):

```
book_trip(request, approval_token)
  -> validate: token valid, not expired, tied to this session,
     tied to this exact booking preview, inventory/price snapshot
     still valid, approval actually occurred, booking parameters
     match the approved parameters
  -> mismatch on any check -> REJECT + require revalidation
  -> all checks pass -> execute booking -> return confirmation
```

Approval token (short-lived, not reusable indefinitely - exact expiry set
from inventory/payment behavior):

```json
{
  "approval_id": "APR-123",
  "session_id": "SESSION-456",
  "booking_preview_id": "PREVIEW-789",
  "inventory_version": "INV-2026-09-23-142",
  "approved_total": 25400,
  "approved_at": "...",
  "expires_at": "...",
  "status": "APPROVED"
}
```

**Permission tiers:**
- **AUTO** - all read-only tools (search, details, retrieval, inventory
  checks, composition, validation).
- **GATE** - booking preview, booking, cancellation; `book_trip` requires
  an explicit, independently-validated approval artifact.
- **DENY** (Phase 1) - no tool exists for changing budget, changing fixed
  dates, charging payment without confirmation, arbitrary external
  purchases, deleting/canceling without explicit flow, or browsing
  arbitrary websites and acting on them. Maps directly to the Phase 0
  autonomy policy.

**MCP boundary:** used where it provides a clean standardized
agent-to-tool-ecosystem interface, not adopted merely because the product
is agentic. If a small controlled tool surface with direct internal
interfaces is simpler for v1, start there and expose an MCP-compatible
boundary once interoperability/reuse actually justifies it. The tool
contract and permission boundary are the requirement; the protocol name
isn't.

## 4. Orchestration design

**Single agent, not multi-agent**, for Phase 1. The task is one coherent
objective (find a viable Goa hotel + activity combination under user
constraints); the complexity is retrieval/search/adaptation/constraint-
reasoning/evaluation/approval, not independent agents with separate goals.
Multi-agent would add inter-agent communication, latency, failure modes,
evaluation complexity and duplicated context without a demonstrated need -
single agent + deterministic orchestration/state machine around it, where
the agent proposes the next action and the orchestrator validates whether
it's legal.

### State machine

```
USER REQUEST -> VALIDATE INPUT -> INITIAL SEARCH -> OBSERVE RESULT
   -> CLASSIFY OUTCOME
        -> VALID VIABLE RESULT -> COMPOSE TRIP -> VALIDATE TRIP
             -> RECOMMENDATION -> USER REVIEW
                  -> ACCEPT -> BOOKING GATE (see below)
                  -> CHANGE -> REPLAN (see below) -> SEARCH
        -> RECOVERABLE FAILURE -> RETRY TOOL (tool_retry_count)
             -> retry, or exhausted -> escalate
        -> CONSTRAINT / TRADE-OFF -> can AUTO adapt?
             -> YES -> ADAPT -> SEARCH
             -> NO  -> ASK
```

### Failure classification (deterministic policy node, not a prompt)

```
TOOL RESULT -> FAILURE CLASSIFIER
   -> RECOVERABLE FAILURE (timeout, transient error) -> RETRY
   -> SAFE AUTO RELAXATION (radius, equivalent substitution,
      granted date flexibility) -> ADAPT -> increment
      adaptation_round_count -> search again
   -> PREFERENCE TRADE-OFF (drop activity, exceed budget, change
      fixed dates, material hotel downgrade) -> ASK
```

At `adaptation_round_count == 3`: transition to FALLBACK -> surface
closest viable alternatives -> ASK. No fourth autonomous relaxation.

### User-triggered replan (separate budget from adaptation)

A user saying "show me another option" is a new search objective, not
evidence the original request failed - carrying the old adaptation
counter forward would let harmless alternative requests falsely exhaust
the original search budget. So:

```
Recommendation -> user: "show me another" -> replan_count += 1,
  adaptation_round_count reset to 0 -> new search
```

Bounded independently: **max 3 user-triggered replans per session**, plus
a **session-wide tool/action call budget** (exact figure set from the
cost/latency benchmark in Section 1, not invented ahead of data). At the
replan limit: "I've shown the available alternatives I can find within
your preferences. Would you like to change one of your constraints?" - no
further autonomous search until the user meaningfully changes the request
or starts a new session.

### Price/availability re-confirm loop (stricter - immediately pre-commitment)

```
User confirms -> revalidate -> MATCH -> book
                             -> CHANGED -> ASK -> user accepts new price
                                  -> revalidate again -> MATCH -> book
                                                       -> CHANGED again -> STOP
```

Max 2 revalidation cycles per booking attempt. After the second mismatch:
"The price or availability changed again, so I can't safely complete this
booking. Please review the latest option and start a new booking
attempt." No infinite loop. A price-change re-confirmation does not
consume adaptation rounds - it's a separate booking-integrity counter.

### State object (structured, not inferred from conversation text)

```json
{
  "destination": "Goa",
  "dates": {},
  "travelers": 2,
  "budget": 30000,
  "preferences": [],
  "hard_constraints": [],
  "allowed_flexibility": {},
  "adaptation_round_count": 2,
  "replan_count": 0,
  "booking_revalidation_count": 0,
  "tool_retry_count": 0,
  "current_candidates": [],
  "selected_candidates": [],
  "pending_tradeoff": null,
  "approval_status": "NOT_REQUIRED"
}
```

Four counters, four distinct product concerns - the model reasons over
this state but does not get to redefine it.

## Final architecture

```
User/UI -> Orchestrator/State Machine -> Agent Model (reasoning/tool selection)
        -> MCP/Tool Interface -> {Hotels, Activities, RAG, Validator/Compose, Booking Preview}
        -> User Approval -> Booking Tool (independently validates freshness/authorization)
```

The separation of reasoning from enforcement is the load-bearing decision
in this RFC: RAG, MCP, model choice and agent reasoning can all evolve
without weakening the Phase 0 autonomy guarantees or the Phase 2
evaluation contract, because none of those guarantees live in the prompt -
they live in the orchestrator and the tools.
