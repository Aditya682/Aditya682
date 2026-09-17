"""The budget/preference guardrail.

Deliberately plain Python, not an LLM call: the JD's "evaluates constraints"
step should be a deterministic numeric check, not a model's judgment about
whether something is within budget. The LLM decides *what* hotel/activities
to propose; this function decides whether that proposal is *allowed*.
"""

from __future__ import annotations

from travel_agent.schemas import BudgetBreakdown, ConstraintReport, ConstraintViolation

MISC_BUFFER_RATIO = 0.15  # reserve 15% of budget for transport/meals/incidentals


def check_constraints(
    hotel: dict,
    activities: list[dict],
    days: int,
    travelers: int,
    budget_inr: int,
    needs_flexible_cancellation: bool,
    wants_beach_hotel: bool,
) -> ConstraintReport:
    nights = max(days - 1, 1)
    hotel_total = hotel["price_per_night_inr"] * nights
    activities_total = sum(a["price_inr"] for a in activities) * travelers
    misc_buffer = round(budget_inr * MISC_BUFFER_RATIO)
    grand_total = hotel_total + activities_total + misc_buffer

    budget = BudgetBreakdown(
        hotel_total_inr=hotel_total,
        activities_total_inr=activities_total,
        misc_buffer_inr=misc_buffer,
        grand_total_inr=grand_total,
        budget_inr=budget_inr,
        within_budget=grand_total <= budget_inr,
    )

    violations: list[ConstraintViolation] = []
    if not budget.within_budget:
        violations.append(
            ConstraintViolation(
                field="budget",
                message=f"Total {grand_total} INR exceeds budget {budget_inr} INR by {grand_total - budget_inr} INR",
            )
        )
    if needs_flexible_cancellation and not hotel["cancellation_flexible"]:
        violations.append(
            ConstraintViolation(field="cancellation", message=f"{hotel['name']} does not offer flexible cancellation")
        )
    if wants_beach_hotel and not hotel["beachfront"]:
        violations.append(
            ConstraintViolation(field="hotel_type", message=f"{hotel['name']} is not beachfront")
        )

    return ConstraintReport(passed=len(violations) == 0, violations=violations, budget=budget)
