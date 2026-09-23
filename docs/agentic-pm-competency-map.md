# Agentic AI PM competency map

A living reference, not a one-time read. Use this alongside `docs/` phase
artifacts (one-pager, eval spec, RFC, etc.) as we build this project, and
reuse it directly for interview prep on other Agentic AI PM applications.

Sources for the JD-side validation: [Novartis - PM, Agentic AI
Solutions](https://www.novartis.com/careers/career-search/job/details/req-10078689-product-manager-agentic-ai-solutions),
[Microsoft AI - Principal PM, Agentic
Experiences](https://microsoft.ai/job/principal-product-manager-agentic-experiences/),
[LangChain - PM,
LangSmith](https://jobs.ashbyhq.com/langchain/27af5f96-b287-4bcc-8679-f96686dc7c8d),
[Harvard HBS AI Institute - Agentic AI
PM](https://careers.harvard.edu/job/agentic-ai-product-manager-hbs-ai-institute-in-boston-ma-united-states-jid-1015),
[IFS Loops - PM, Agentic
AI](https://theloops.io/career/product-manager-agentic-ai/), [RiffOn -
Evaluation Metrics as the PRD for
Engineers](https://riffon.com/insight/ins_mahklkxy8zmc).

## The one-line distinction

> Weak AI PM: "I know LLMs, RAG, MCP and LangGraph."
> Strong AI PM: "I can decide when an agent is appropriate, define the
> workflow and tools it needs, determine what context it should retrieve,
> specify how it should behave and recover from failure, define evaluation
> and guardrails, and measure whether it actually improves the user's
> outcome."

Knowing the vocabulary is table stakes. The job is the chain: **business
problem -> is AI/an agent even appropriate -> system design -> data/tools/
context -> agent behavior spec -> evaluation -> guardrails -> ship ->
observe -> improve.**

## How to use this doc with the project's 6 phases

The 6 phases (tracked as tasks) are *when* you do PM work on this project.
This map is *what you draw on* at each point - not a separate track.

| Project phase | Competency layers it pulls from |
|---|---|
| 1. Strategy & framing | Problem discovery, UX intent, "is this even an agent problem" |
| 2. Eval-driven spec | Evaluation, golden datasets, LLM-as-judge, trajectory design, guardrails |
| 3. Feasibility RFC | Intelligence (model choice), context (RAG/memory), tools/MCP, orchestration (single vs multi-agent) |
| 4. Build sprints | All of the above, applied - acceptance criteria per milestone |
| 5. Launch readiness | Safety/autonomy levels, production (observability, latency, cost) |
| 6. Iteration | Learning loop - feedback, experiments, monitoring |

## The 10 layers

| Layer | What the PM actually does |
|---|---|
| 1. Problem | Find the right problem for AI/agents - and be willing to say "we don't need an agent here" |
| 2. UX | Design how the user interacts with the agent (transparency, confirmation, error recovery, handoff) |
| 3. Intelligence | Decide model/reasoning architecture and the criteria behind that choice |
| 4. Context | RAG, memory, knowledge - what the agent should know and how fresh it needs to be |
| 5. Tools | APIs, function calling, MCP - what the agent can *do*, not just say |
| 6. Orchestration | Single agent vs. workflow vs. multi-agent |
| 7. Evaluation | Define whether the system is actually good - golden datasets, LLM-as-judge, trajectory success |
| 8. Safety | Guardrails, permissions, human-in-the-loop, autonomy levels (AUTO / GATE / DENY) |
| 9. Production | Observability, latency, cost, reliability |
| 10. Learning | Feedback, experiments, monitoring, iteration |

## Problem discovery - before any architecture

Is this even an agent problem? Three tiers, cheapest-first:

- **Single LLM call** - simple generation/classification/extraction.
- **Workflow** - a predictable multi-step process; use this when
  predictability/compliance matters more than adaptability.
- **Agent** - plan -> act -> observe -> repeat; justified only when
  adaptability or open-ended reasoning is actually required.

Questions to answer before writing a line of code: What user problem are we
solving? How is it solved today? How many steps, and where does human
judgment occur? Is the workflow deterministic, and where does ambiguity
enter? What information does the user need, what actions need to happen,
and what happens if the AI is wrong? Is the added autonomy worth the added
complexity?

## RAG - the product-level questions, not the algorithm

**Knowledge:** What data should the agent access? Which sources are
authoritative? How often does it change?
**Retrieval:** Keyword vs. semantic vs. hybrid? Top-K? Metadata filtering?
Re-ranking?
**Quality:** Are we retrieving the right documents? Is the answer grounded?
Is the model hallucinating? Are citations required?
**Metrics:** Retrieval recall, Precision@K, NDCG@K, answer groundedness,
answer relevance, citation accuracy, task success, user feedback.

You don't implement the retrieval algorithm. You need to know which
failure you're looking at and which product/engineering lever fixes it.

## Embeddings & vector DBs - product questions

What should be embedded vs. kept as metadata? How should documents be
chunked, and what's the retrieval unit? What counts as "similar" for this
domain? How do we handle freshness, permissions, and the empty-result case?

## Agents - the loop

`Goal -> Plan -> Choose tool -> Execute -> Observe result -> Reason -> Next
action -> Validate -> Finish / escalate`

This is the structural difference from a normal AI PM's `Prompt -> Model ->
Response`.

## Single agent vs. multi-agent

The PM decides: do we need multiple agents at all? What is each one
responsible for? How do they communicate, what state is shared, when do
they run in parallel vs. sequentially, and what happens when one fails?
Common patterns: orchestrator/router, workers, evaluators, reflection,
sequential coordination, parallel execution, intent-based routing.

## Tool calling / function calling

The agent is only useful once it can *do* things, not just talk. Product
questions live in the failure path as much as the happy path: what happens
when the tool call fails, when the API times out, when the agent picks the
wrong tool.

## MCP - what it actually is for a PM

Not "another AI framework" - a standardized context/tool integration layer
(JSON-RPC-based) so an LLM can interact with external tools, databases and
services without a bespoke integration per agent. PM questions: which tools
should the agent expose? What permissions does each carry - read-only vs.
mutating? How do we authenticate and audit tool calls? What happens on tool
failure? How do we stop the agent from calling the wrong tool?

The real question isn't "can we use MCP" - it's "what integration
architecture makes the agent secure, reusable, observable and
maintainable."

## Agent memory

Short-term (current task state), episodic (what happened in prior tasks),
semantic (persistent facts), vector (retrieval-based). PM decisions: what
should persist, for how long, who owns it, can the user correct/delete it,
what happens when memory conflicts with current data.

## Prompt engineering & structured outputs

Not becoming a prompt engineer - but understanding system instructions +
user intent + retrieved context + tool results + conversation state +
output schema as one composed unit, and why downstream components need a
schema (enums, required fields, validation, fallback behavior) rather than
"probably restart the pipeline."

## Evaluation - the biggest gap between an ordinary PM and a strong Agentic PM

Three distinct questions, not one: is the *model* capable, does the
*application* produce useful answers, did the *agent* accomplish the task
correctly (the trajectory, not just the final output).

**What to measure:**
- RAG: retrieval precision/recall, NDCG, groundedness, answer relevance
- Router: correct tool selected? correct parameters extracted?
- Tool execution: correct tool, correct params, successful execution,
  recovery after failure
- Trajectory: was the *whole path* correct, not just the destination
- Business outcome: did the user actually accomplish the task

**LLM-as-judge:** golden dataset -> agent -> output -> judge -> score. But
the judge itself needs evaluating: does it agree with human raters? What's
its false-positive rate? Can the judge regress? Are we even judging the
right dimension?

**Golden datasets:** 50-100 representative tasks with expected outcomes,
re-run on every model/prompt/RAG/tool/agent-workflow/MCP-server change.
This *is* evaluation-driven development.

## Observability / tracing

Production agents need traces covering: where latency occurred, which tool
was called, which retrieval happened, which prompt version ran, why a run
failed, token consumption, cost, retries, hallucinations, escalations.

## Guardrails & autonomy levels

Four layers: input guardrails (injection, malicious input, sensitive
data), retrieval guardrails (permission filtering, trusted sources,
staleness), output guardrails (unsafe content, unsupported claims), agentic
guardrails (tool permissions, max steps, budget limits, allowed-tool list).

Autonomy levels per action, not per agent:

| Mode | Meaning | Example |
|---|---|---|
| AUTO | Agent acts independently | Search logs, read database |
| GATE | Agent proposes, human approves | Restart a service, update a record |
| DENY | Agent cannot perform the action at all | Delete production data |

## Reliability - the compounding-failure math

Five sequential steps at 92% success each: `0.92^5 ≈ 66%` end-to-end.
Individually "good" components can still produce a bad agent. This is why
shorter trajectories, fewer unnecessary steps, and well-placed human
escalation are themselves product decisions, not just engineering
concerns.

## Cost & latency

The PM balances intelligence vs. cost vs. latency vs. reliability -
including deciding when a smaller/cheaper model is the *better* product
decision (e.g. small model for routing, large model for reasoning,
deterministic code for execution - no model call at all).

## Model selection criteria (not the model itself)

Quality, latency, cost, context window, tool-calling reliability,
structured-output reliability, privacy/data handling, API availability.
Engineering benchmarks against these criteria; the PM sets them.

## Product UX for agents

Conversation, transparency ("Searching customer records...", "Found 3
relevant documents..."), confirmation before consequential actions, error
recovery ("I couldn't access X - retry?"), human handoff, and making the
agent's current state legible to the user at all times.

## Failure handling as a first-class spec, not an afterthought

`Agent -> API -> ERROR ->` retry / alternative tool / ask user / escalate
to human / fail gracefully. This should be written down as a product
requirement, not left implicit for engineering to improvise.

## Security & permissions

Least privilege as the default posture: the agent should have only the
permissions required for its task. Authentication, authorization, tenant
isolation, PII handling, secrets, audit logs, tool-level permissions,
prompt injection, data exfiltration.

## Business/product metrics - where you distinguish from an AI engineer

Don't stop at "accuracy = 87%." Four tiers:
- **User:** task completion, adoption, repeat usage, retention, satisfaction
- **AI:** groundedness, tool accuracy, trajectory success, hallucination rate
- **Operational:** latency, cost/task, tool failure rate, escalation rate
- **Business:** time saved, conversion, revenue impact, support cost,
  operational efficiency

A concrete outcome number ("15-step workflow reduced to under 10 seconds")
is far more compelling than "built an agent."

## Experimentation & rollout

`Hypothesis -> Prototype -> Golden evaluation -> User testing -> Production
-> A/B or controlled rollout -> Measure -> Iterate.` Safe rollout staging:
internal testing -> shadow mode -> small customer cohort -> human-approval
mode -> expanded rollout -> autonomous mode - monitoring failures,
escalations, cost, latency, safety and feedback at every stage.

## Post-launch: the self-improving loop

`Production -> Trace -> Failure -> Classify -> Golden dataset -> Fix ->
Evaluate -> Deploy.` Agentic products are not "build -> launch -> done."

## What "technical PM" means in these JDs

Comfortable discussing APIs, JSON, REST, webhooks, databases, vector
databases, embeddings, RAG, LLMs, prompts, tool calling, agents,
orchestration, MCP, cloud, observability, evaluation, security, latency,
cost. Not "must personally write all the code."

## What hiring managers are actually screening for

Can you identify the right AI problem? Understand the technical
architecture? Translate that into product requirements? Work with ML/AI
engineers? Define evaluation? Reason about agent failure modes? Design
safe autonomy? Understand RAG/tool/MCP architecture well enough to make
tradeoffs? Measure production performance? Turn all of that into
customer/business outcomes?

## Full prep sequence

Problem discovery -> LLM -> RAG -> embeddings/vector DB -> prompting ->
structured outputs -> tools/function calling -> APIs -> MCP -> agents ->
orchestration -> multi-agent -> memory -> evaluation -> golden datasets ->
LLM judges -> tracing/observability -> guardrails -> HITL -> security ->
reliability -> latency -> cost -> experimentation -> production monitoring
-> business metrics.

## What this specific project is for

Cross-referencing prior experience against this map: Aura gives real
"Strong" evidence for agentic workflows, tool invocation, guardrails, and
MCP; Seek Search gives real "Strong" evidence for RAG, semantic search,
embeddings and vector DB (Milvus). The self-identified gaps were golden
datasets, LLM-as-judge, observability/tracing, agent cost optimization,
production AI monitoring, and travel AI specifically.

This project is built to close exactly those gaps with a real (if small)
system, not a reading list: `evals/` for golden datasets + LLM-as-judge,
`travel_agent/trace.py` for observability, `travel_agent/config.py`'s
model-per-role split for cost reasoning, and the domain itself for the
travel-AI gap. The 6-phase structure exists so the *evidence* is a set of
PM artifacts (one-pager, eval spec, RFC, guardrail policy, iteration
backlog) you can actually point to, not just working code.
