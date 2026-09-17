"""Planner / decomposition node: turns the free-text request into a
TripRequest via structured output. This is the "understand the goal"
step every other agent depends on."""

from __future__ import annotations

from travel_agent.config import AGENT_MODEL
from travel_agent.llm import get_client
from travel_agent.schemas import TripRequest
from travel_agent.trace import traced

SYSTEM_PROMPT = """You turn a free-text trip request into structured fields.
Rules:
- If the traveler mentions "beach hotel", "beachfront", "on the beach", set wants_beach_hotel=true.
- If they mention "flexible cancellation", "refundable", or "free cancellation", set needs_flexible_cancellation=true.
- sightseeing_days should reflect how many days they explicitly want dedicated to sightseeing/touring
  (as opposed to unscheduled beach time). If unstated, use 1.
- budget_inr is the TOTAL trip budget stated (not per-day, not per-person) unless the text says otherwise.
- Put anything you can't fit into the other fields into notes.
"""


@traced("parse_request")
def parse_request_node(state: dict) -> dict:
    client = get_client()
    response = client.messages.parse(
        model=AGENT_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": state["raw_query"]}],
        output_format=TripRequest,
    )
    trip_request: TripRequest = response.parsed_output
    return {"trip_request": trip_request}
