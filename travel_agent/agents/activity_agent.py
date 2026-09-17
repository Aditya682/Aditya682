"""Activity/sightseeing research agent - same tool-use + constrained-selection
pattern as hotel_agent.py, but selects a small set instead of a single item."""

from __future__ import annotations

import json

from anthropic import beta_tool

from travel_agent.config import AGENT_MODEL
from travel_agent.llm import get_client
from travel_agent.rag import retrieve_context
from travel_agent.tools.activity_search import search_activities
from travel_agent.trace import traced


def _build_tool(capture: dict):
    @beta_tool
    def search_activities_tool(category: str | None = None, max_price_inr: int | None = None) -> str:
        """Search sightseeing/leisure/adventure activities.

        Args:
            category: One of "sightseeing", "leisure", "adventure", or None for all.
            max_price_inr: Upper bound on price per person, in INR.
        """
        results = search_activities(category=category, max_price_inr=max_price_inr)
        capture["last_results"] = results
        capture["calls"].append({"category": category, "max_price_inr": max_price_inr})
        return json.dumps(results)

    return search_activities_tool


@traced("research_activities")
def research_activities_node(state: dict) -> dict:
    trip = state["trip_request"]
    retry_feedback = state.get("retry_feedback", "")
    tips_context = retrieve_context("how many activities to plan per day budget", k=2)

    capture = {"last_results": [], "calls": []}
    tool = _build_tool(capture)
    client = get_client()

    target_count = max(1, min(3, trip.sightseeing_days + 1))

    system = f"""You are the activity-research agent for a trip-planning system.
Trip: {trip.destination}, {trip.days} days, {trip.travelers} traveler(s), total budget {trip.budget_inr} INR.
Traveler wants {trip.sightseeing_days} day(s) of sightseeing.

Planning guidance:
{tips_context}

{f"Feedback from the previous attempt: {retry_feedback}" if retry_feedback else ""}

Call search_activities_tool (category="sightseeing" first, since that matches the traveler's explicit
request) to find candidates. You may call it more than once to also check "leisure" options if useful.
Stop once you have enough candidates to choose from (do not call more than 3 times)."""

    runner = client.beta.messages.tool_runner(
        model=AGENT_MODEL,
        max_tokens=2048,
        system=system,
        tools=[tool],
        messages=[{"role": "user", "content": "Find activity candidates for this trip."}],
    )
    for _ in runner:
        pass

    candidates = capture["last_results"]
    if not candidates:
        return {"activity_candidates": [], "selected_activities": [], "activity_search_calls": capture["calls"]}

    names = [c["name"] for c in candidates]
    selection = client.messages.create(
        model=AGENT_MODEL,
        max_tokens=512,
        system=f"Pick exactly {target_count} activities that best fit the trip from the candidate list. Respond with only the chosen names.",
        messages=[
            {
                "role": "user",
                "content": f"Trip: {trip.sightseeing_days} sightseeing day(s), budget_inr={trip.budget_inr}.\nCandidates:\n{json.dumps(candidates, indent=2)}",
            }
        ],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "chosen_activity_names": {
                            "type": "array",
                            "items": {"type": "string", "enum": names},
                            "minItems": target_count,
                            "maxItems": target_count,
                        }
                    },
                    "required": ["chosen_activity_names"],
                    "additionalProperties": False,
                },
            }
        },
    )
    chosen_names = json.loads(next(b.text for b in selection.content if b.type == "text"))["chosen_activity_names"]
    selected = [c for c in candidates if c["name"] in chosen_names]

    return {"activity_candidates": candidates, "selected_activities": selected, "activity_search_calls": capture["calls"]}
