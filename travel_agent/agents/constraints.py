"""Constraint-checker node. Pure Python guardrail - see
tools/constraint_check.py for why this is deliberately not an LLM call."""

from __future__ import annotations

from travel_agent.config import MAX_RESEARCH_RETRIES
from travel_agent.tools.constraint_check import check_constraints
from travel_agent.trace import traced


@traced("check_constraints")
def check_constraints_node(state: dict) -> dict:
    trip = state["trip_request"]
    hotel = state.get("selected_hotel")
    activities = state.get("selected_activities", [])

    retry_count = state.get("retry_count", 0)
    can_retry = retry_count < MAX_RESEARCH_RETRIES

    if hotel is None:
        return {
            "constraint_report": None,
            "constraint_passed": False,
            "retry_count": retry_count + 1,
            "can_retry": can_retry,
            "retry_feedback": "No hotel candidates matched the search filters - widen the search (e.g. drop the price cap on the first pass).",
        }

    report = check_constraints(
        hotel=hotel,
        activities=activities,
        days=trip.days,
        travelers=trip.travelers,
        budget_inr=trip.budget_inr,
        needs_flexible_cancellation=trip.needs_flexible_cancellation,
        wants_beach_hotel=trip.wants_beach_hotel,
    )

    feedback = ""
    if not report.passed:
        feedback = "; ".join(v.message for v in report.violations) + ". Prefer cheaper / more compliant options this time."

    return {
        "constraint_report": report,
        "constraint_passed": report.passed,
        "retry_count": retry_count + (0 if report.passed else 1),
        "can_retry": can_retry,
        "retry_feedback": feedback,
    }
