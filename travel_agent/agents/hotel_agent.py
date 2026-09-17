"""Hotel research agent.

Two-step pattern, deliberately not a single free-form LLM call:
1. Tool use - Claude decides the search filters (via the real Anthropic
   tool runner) and calls search_hotels, a deterministic function backed by
   the mock inventory.
2. Constrained selection - Claude picks ONE hotel from the *actual* returned
   candidates via a JSON-schema `enum` of real names, so it cannot invent a
   hotel that isn't in the inventory (a directly checkable anti-hallucination
   guardrail, not a prompt instruction hoping it behaves).
"""

from __future__ import annotations

import json

from anthropic import beta_tool

from travel_agent.config import AGENT_MODEL
from travel_agent.llm import get_client
from travel_agent.rag import retrieve_context
from travel_agent.tools.hotel_search import search_hotels
from travel_agent.trace import traced


def _build_tool(capture: dict):
    @beta_tool
    def search_hotels_tool(
        beachfront: bool | None = None,
        max_price_per_night_inr: int | None = None,
        cancellation_flexible: bool | None = None,
    ) -> str:
        """Search the Goa hotel inventory. Pass None for any filter you don't want to apply.

        Args:
            beachfront: True to only return beachfront hotels.
            max_price_per_night_inr: Upper bound on price per night, in INR.
            cancellation_flexible: True to only return hotels with free cancellation.
        """
        results = search_hotels(
            beachfront=beachfront,
            max_price_per_night_inr=max_price_per_night_inr,
            cancellation_flexible=cancellation_flexible,
        )
        capture["last_results"] = results
        capture["calls"].append(
            {"beachfront": beachfront, "max_price_per_night_inr": max_price_per_night_inr, "cancellation_flexible": cancellation_flexible}
        )
        return json.dumps(results)

    return search_hotels_tool


@traced("research_hotels")
def research_hotels_node(state: dict) -> dict:
    trip = state["trip_request"]
    retry_feedback = state.get("retry_feedback", "")
    area_context = retrieve_context(f"{trip.destination} beach areas budget", k=2)

    capture = {"last_results": [], "calls": []}
    tool = _build_tool(capture)
    client = get_client()

    system = f"""You are the hotel-research agent for a trip-planning system.
Trip: {trip.destination}, {trip.days} days, {trip.travelers} traveler(s), total budget {trip.budget_inr} INR.
Wants beachfront hotel: {trip.wants_beach_hotel}. Needs flexible cancellation: {trip.needs_flexible_cancellation}.

Relevant area knowledge:
{area_context}

{f"Feedback from the previous attempt (which failed constraint checks): {retry_feedback}" if retry_feedback else ""}

Call search_hotels_tool with filters matching the traveler's stated preferences.
As a rough guide, hotel spend should stay under ~55% of the total budget across all nights - if your
first search returns only options that would clearly blow that, call the tool again with a lower
max_price_per_night_inr. Stop once you have a reasonable candidate set (do not call the tool more than 3 times)."""

    runner = client.beta.messages.tool_runner(
        model=AGENT_MODEL,
        max_tokens=2048,
        system=system,
        tools=[tool],
        messages=[{"role": "user", "content": "Find hotel candidates for this trip."}],
    )
    for _ in runner:
        pass  # side effects captured via `capture`; we don't need the free-text summary

    candidates = capture["last_results"][:5]
    if not candidates:
        return {"hotel_candidates": [], "selected_hotel": None, "hotel_search_calls": capture["calls"]}

    names = [c["name"] for c in candidates]
    selection = client.messages.create(
        model=AGENT_MODEL,
        max_tokens=256,
        system="Pick the single best hotel for the stated trip from the candidate list. Respond with only the chosen hotel's exact name.",
        messages=[
            {
                "role": "user",
                "content": f"Trip preferences: beachfront={trip.wants_beach_hotel}, flexible_cancellation={trip.needs_flexible_cancellation}, budget_inr={trip.budget_inr}.\nCandidates:\n{json.dumps(candidates, indent=2)}",
            }
        ],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {"chosen_hotel_name": {"type": "string", "enum": names}},
                    "required": ["chosen_hotel_name"],
                    "additionalProperties": False,
                },
            }
        },
    )
    chosen_name = json.loads(next(b.text for b in selection.content if b.type == "text"))["chosen_hotel_name"]
    selected = next(c for c in candidates if c["name"] == chosen_name)

    return {"hotel_candidates": candidates, "selected_hotel": selected, "hotel_search_calls": capture["calls"]}
