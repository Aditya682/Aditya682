"""Itinerary composer.

Factual data (hotel record, budget numbers) comes straight from the earlier
tool-backed steps - the LLM never re-states a price or a hotel name from
memory. It's only asked for the part that's genuinely generative: how to
sequence the days and why this combination was chosen. That output is
still schema-constrained (structured output), just a narrower schema than
the full Itinerary.
"""

from __future__ import annotations

from pydantic import BaseModel

from travel_agent.config import AGENT_MODEL
from travel_agent.llm import get_client
from travel_agent.schemas import DayPlan, HotelOption, Itinerary
from travel_agent.trace import traced


class _ItineraryNarrative(BaseModel):
    day_plans: list[DayPlan]
    rationale: str


@traced("compose_itinerary")
def compose_itinerary_node(state: dict) -> dict:
    trip = state["trip_request"]
    hotel = state["selected_hotel"]
    activities = state.get("selected_activities", [])
    report = state["constraint_report"]

    client = get_client()
    response = client.messages.parse(
        model=AGENT_MODEL,
        max_tokens=2048,
        system=(
            "You write day-by-day trip itineraries. You are given the ALREADY-CHOSEN hotel and "
            "activities (do not change or invent them) - your job is only to sequence them across "
            "the trip's days sensibly (e.g. arrival/checkout logistics, spacing sightseeing so it "
            "isn't back-to-back every day) and explain the choice in one short rationale paragraph."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Destination: {trip.destination}\nDays: {trip.days}\nTravelers: {trip.travelers}\n"
                    f"Hotel: {hotel}\nActivities: {activities}\n"
                    f"Budget status: {'within budget' if report.passed else 'OVER budget - mention the tradeoff in the rationale'}, "
                    f"total {report.budget.grand_total_inr} INR of {report.budget.budget_inr} INR budget."
                ),
            }
        ],
        output_format=_ItineraryNarrative,
    )
    narrative: _ItineraryNarrative = response.parsed_output

    itinerary = Itinerary(
        destination=trip.destination,
        days=trip.days,
        travelers=trip.travelers,
        hotel=HotelOption(**hotel),
        day_plans=narrative.day_plans,
        budget=report.budget,
        rationale=narrative.rationale,
    )
    return {"itinerary": itinerary}
