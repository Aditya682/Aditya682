"""Human-in-the-loop approval gate.

Uses LangGraph's native `interrupt()` - the graph genuinely pauses and
returns control to the caller (see travel_agent/graph.py and cli.py for the
invoke/resume flow), it does not just print a warning and continue. Nothing
past this node runs until a human (or an eval harness standing in for one)
calls back in with a decision.
"""

from __future__ import annotations

from langgraph.types import interrupt

from travel_agent.trace import traced


@traced("approval_gate")
def approval_gate_node(state: dict) -> dict:
    itinerary = state["itinerary"]
    decision = interrupt(
        {
            "type": "approval_request",
            "message": "Review this itinerary. No booking action will be taken until you approve it.",
            "itinerary": itinerary.model_dump(),
        }
    )
    return {"approved": bool(decision)}
