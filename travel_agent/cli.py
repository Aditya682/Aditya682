"""Run one trip request end-to-end from the terminal, including the
human-in-the-loop approval prompt.

Usage:
    python -m travel_agent.cli "Plan a 5-day Goa trip for 2 people under
    INR 50000. We prefer a beach hotel, want one day of sightseeing, and
    flexible cancellation."
"""

from __future__ import annotations

import json
import sys
import uuid

from dotenv import load_dotenv
from langgraph.types import Command

from travel_agent.graph import build_graph
from travel_agent.trace import Tracer

load_dotenv()


def _print_itinerary(itinerary: dict) -> None:
    print("\n" + "=" * 60)
    print(f"ITINERARY - {itinerary['destination']} ({itinerary['days']} days, {itinerary['travelers']} traveler(s))")
    print("=" * 60)
    print(f"Hotel: {itinerary['hotel']['name']} ({itinerary['hotel']['area']}) - "
          f"{itinerary['hotel']['price_per_night_inr']} INR/night, "
          f"beachfront={itinerary['hotel']['beachfront']}, "
          f"flexible_cancellation={itinerary['hotel']['cancellation_flexible']}")
    for day in itinerary["day_plans"]:
        print(f"\nDay {day['day_number']}: {day['theme']}")
        for a in day["activities"]:
            print(f"  - {a}")
        if day["notes"]:
            print(f"  note: {day['notes']}")
    budget = itinerary["budget"]
    print(f"\nBudget: {budget['grand_total_inr']} INR of {budget['budget_inr']} INR "
          f"({'within budget' if budget['within_budget'] else 'OVER BUDGET'})")
    print(f"  hotel: {budget['hotel_total_inr']} | activities: {budget['activities_total_inr']} | buffer: {budget['misc_buffer_inr']}")
    print(f"\nRationale: {itinerary['rationale']}")
    print("=" * 60 + "\n")


def run_trip_request(raw_query: str, auto_approve: bool | None = None) -> dict:
    """Runs the graph to completion. If auto_approve is None, prompts on
    the terminal at the approval gate; otherwise uses the given bool
    (used by the eval harness so it can run unattended)."""
    graph = build_graph()
    session_id = uuid.uuid4().hex[:12]
    tracer = Tracer(session_id)
    config = {"configurable": {"thread_id": session_id}}

    result = graph.invoke({"raw_query": raw_query, "_tracer": tracer}, config)

    if "__interrupt__" not in result:
        return {"session_id": session_id, "final_state": result}

    payload = result["__interrupt__"][0].value
    if auto_approve is None:
        _print_itinerary(payload["itinerary"])
        answer = input("Approve this itinerary and place a booking hold? [y/N]: ").strip().lower()
        decision = answer == "y"
    else:
        decision = auto_approve

    result = graph.invoke(Command(resume=decision), config)
    return {"session_id": session_id, "final_state": result}


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m travel_agent.cli \"<trip request>\"")
        sys.exit(1)
    raw_query = sys.argv[1]
    outcome = run_trip_request(raw_query)
    final = outcome["final_state"]

    if final.get("booking"):
        print("Booking confirmed:")
        print(json.dumps(final["booking"], indent=2))
    elif final.get("itinerary") and not final.get("approved", True):
        print("Itinerary was not approved - no booking action taken.")
    elif not final.get("constraint_passed", True):
        print("Could not find an itinerary that satisfies the stated constraints after retrying.")
        report = final.get("constraint_report")
        if report:
            for v in report.violations:
                print(f"  - {v.field}: {v.message}")
    print(f"\nSession id: {outcome['session_id']} (trace: traces/{outcome['session_id']}.jsonl)")


if __name__ == "__main__":
    main()
