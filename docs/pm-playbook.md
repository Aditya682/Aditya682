# PM playbook - Goa trip planner

The concrete "how": for each of the 6 project phases, which competency-map
layers you're drawing on, which questions you answer in writing, and what
artifact comes out the other end. This is the process; the content is
yours to produce.

## Why this exact project, grounded in real travel-tech roles

This isn't a generic agent exercise - it's the same shape of work as live
postings: Navan's "Product Manager - Book with AI" owns a booking agent
end-to-end and is explicitly responsible for defining "meaningful goals
and evaluation criteria for AI behavior: task completion, factual
accuracy, policy compliance, correct tool and UI usage, response quality,
latency, and safe recovery from failures" - and for keeping the agent
"transparent about limitations, unsupported requests, changing prices,
availability, and booking status." That is Phase 2 and Phase 5 of this
playbook, close to word for word. Expedia runs multiple live PM roles on
the same pattern (Personal AI Agents, Agentic Search, B2B AI Solutions -
"generative and agentic AI modules that power smarter search, decisioning,
and trip support"). MakeMyTrip's Myra assistant is built the same way this
project is: specialized agents per domain (flights, accommodation,
ground transport, visas) under one orchestrator - here, hotels and
activities. Sources: [Navan - PM, Book with
AI](https://www.dreamworkhq.com/job/dd39bb23-0a00-40b8-ac78-f76ef1e352d0),
[Expedia - Principal PM, Personal AI
Agents](https://careers.expediagroup.com/job/principal-product-manager-personal-ai-agents/san-jose-ca/R-104243/),
[Expedia - PM II, Agentic
Search](https://www.tealhq.com/job/product-manager-ii-agentic-search_7ea1a98ae100888d7e8eed70e3a765994ab7f),
[MakeMyTrip GenAI Trip Planning
Assistant](https://investors.mmtcdn.com/Press_Release_Gen_AI_Trip_Planning_Assistant_07_08_2025_404cc1872a.pdf).

## Phase 0: Problem discovery (Layer 1) - do this before Phase 1

Walk the decision tree explicitly, in writing, for this exact scenario -
don't skip to "obviously it's an agent":

1. **Single LLM call, workflow, or agent?** Is the task deterministic once
   inputs are known, or does it require adapting mid-task (a constraint
   fails, retry with different parameters)? Does it need to evaluate
   multiple options and choose, or just transform one input to one output?
2. Answer the standard discovery questions for *this* scenario specifically:
   - What's actually the user problem - comparing hotel+activity+budget
     combinations by hand, or something narrower?
   - How is it solved today (manually)? Walk the real steps a person takes.
   - How many steps, and where does human judgment currently sit?
   - Is the workflow deterministic, or where does ambiguity enter (NL
     request parsing, option tradeoffs)?
   - What happens if the AI is wrong - and does that answer differ between
     "recommends a bad hotel" vs. "books a bad hotel"? (This is where your
     autonomy boundary comes from, not from a generic "agents are risky.")
3. Write the verdict as one paragraph: is autonomy worth the complexity
   here, and specifically *where* in the flow - all of it, or just the
   research/comparison part?

This paragraph becomes the "why agentic" section of the one-pager - don't
write that section until you've done this.

## Phase 1: One-pager (Layers 1-2)

Template already given. One addition: sketch the transparency/confirmation
UX (Layer 2) as a short script - what does the user actually see at each
step ("Searching hotels...", "Found 3 matching your budget...", "Here's
the itinerary - approve to place a hold?"). That's a product decision, not
an implementation detail, and it directly determines what your trace/log
events need to capture later.

## Phase 2: Eval-driven spec (Evaluation + Safety layers)

Write this *before* any code, as the actual spec engineering builds
against:

1. **Golden dataset shape** - what does one test case look like (input
   query, expected structured fields, expected pass/fail behavior)? How
   many cases, and what varies across them (tight budget, no preference,
   impossible request)?
2. **Trajectory spec** - max steps before giving up, retry policy, what
   "cannot fulfill" looks like as a first-class outcome (not a crash).
3. **Judge rubric** - which dimensions matter, and critically: how would
   you check the judge agrees with a human rater on a sample? (If you
   can't answer this, the judge is unvalidated - say so as an open risk,
   don't skip it.)
4. **Guardrail table** - every action the system can take, mapped to
   AUTO / GATE / DENY, with one line of reasoning each.

## Phase 3: Feasibility RFC (Intelligence, Context, Tools, Orchestration layers)

1. **Model selection** - don't inherit defaults; justify per role (agent
   vs. judge) against the criteria table: quality, latency, cost, context,
   tool-calling reliability, structured-output reliability.
2. **Context/RAG design** - what should be retrieved, from what corpus,
   how fresh does it need to be, what's the failure mode when nothing
   relevant is found.
3. **Tools/MCP design** - list each tool: inputs, outputs, read-only vs.
   mutating, permission tier.
4. **Orchestration design** - single agent or multiple, and *why*. Sketch
   the state diagram yourself before looking at any reference
   implementation.

This is the technical RFC - the handoff point from "PM decides" to
"engineering builds."

## Phase 4: Build sprints

Per milestone: write 3-5 acceptance criteria *before* building (a real
ticket, not a vague description). After building: check against the
Phase 2 eval spec, log a ship/no-ship line with reasoning - especially
when the answer is "ship with a known gap," which is a real, common PM
call, not a failure.

## Phase 5: Launch readiness (Safety + Production layers)

- Finalize the guardrail table from Phase 2 against what you actually
  built - did anything change?
- Monitoring requirements: what should the trace data surface - latency
  per node, tool failure rate, retry rate, approval-rejection rate,
  cost/session. Write these as requirements before checking what the
  trace file already captures.

## Phase 6: Iteration

Run the eval suite, look at every failure, classify by root cause
(retrieval miss, constraint-logic bug, judge miscalibration, prompt
issue), then write a prioritized backlog with reach/impact reasoning per
item - not just a flat bug list.
