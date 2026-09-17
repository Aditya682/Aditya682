"""Booking node - only reachable after approval_gate_node returns approved=True."""

from __future__ import annotations

from travel_agent.tools.booking import create_booking_hold
from travel_agent.trace import traced


@traced("book")
def book_node(state: dict) -> dict:
    itinerary = state["itinerary"]
    booking = create_booking_hold(
        destination=itinerary.destination,
        hotel_name=itinerary.hotel.name,
        days=itinerary.days,
        travelers=itinerary.travelers,
        grand_total_inr=itinerary.budget.grand_total_inr,
    )
    return {"booking": booking}
