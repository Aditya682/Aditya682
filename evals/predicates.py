"""Checkable predicates for the golden dataset - the "not vibes-based"
layer of the eval. Each function returns (passed: bool, detail: str).
These check facts (day count, budget compliance, hotel attributes), not
subjective quality - that's what judge.py is for.
"""

from __future__ import annotations


def evaluate_example(example: dict, final_state: dict) -> dict:
    checks: dict[str, tuple[bool, str]] = {}
    itinerary = final_state.get("itinerary")

    if not example["expect_fulfillable"]:
        no_itinerary = itinerary is None
        correctly_declined = not final_state.get("constraint_passed", True)
        checks["correctly_declined_infeasible_request"] = (
            no_itinerary and correctly_declined,
            "system should refuse (no itinerary, constraints failed) rather than fabricate a non-compliant plan"
            if not (no_itinerary and correctly_declined)
            else "ok",
        )
        return _finalize(example, checks)

    if itinerary is None:
        checks["itinerary_produced"] = (False, "expected a fulfillable request to produce an itinerary, got none")
        return _finalize(example, checks)

    checks["itinerary_produced"] = (True, "ok")
    checks["destination_matches"] = (
        example["expected_destination"].lower() in itinerary.destination.lower(),
        f"expected destination containing '{example['expected_destination']}', got '{itinerary.destination}'",
    )
    checks["days_match"] = (
        itinerary.days == example["expected_days"],
        f"expected {example['expected_days']} days, got {itinerary.days}",
    )
    checks["travelers_match"] = (
        itinerary.travelers == example["expected_travelers"],
        f"expected {example['expected_travelers']} travelers, got {itinerary.travelers}",
    )
    checks["day_plan_count_matches_days"] = (
        len(itinerary.day_plans) == itinerary.days,
        f"expected {itinerary.days} day plans, got {len(itinerary.day_plans)}",
    )
    checks["within_budget"] = (
        itinerary.budget.within_budget,
        f"itinerary total {itinerary.budget.grand_total_inr} INR exceeds budget {itinerary.budget.budget_inr} INR"
        if not itinerary.budget.within_budget
        else "ok",
    )

    if example.get("expect_beachfront") is not None:
        checks["beachfront_matches"] = (
            itinerary.hotel.beachfront == example["expect_beachfront"],
            f"expected beachfront={example['expect_beachfront']}, got {itinerary.hotel.beachfront}",
        )
    if example.get("expect_flexible_cancellation") is not None:
        checks["cancellation_matches"] = (
            itinerary.hotel.cancellation_flexible == example["expect_flexible_cancellation"],
            f"expected cancellation_flexible={example['expect_flexible_cancellation']}, got {itinerary.hotel.cancellation_flexible}",
        )

    return _finalize(example, checks)


def _finalize(example: dict, checks: dict[str, tuple[bool, str]]) -> dict:
    passed = all(ok for ok, _ in checks.values())
    return {
        "id": example["id"],
        "passed": passed,
        "checks": {name: {"passed": ok, "detail": detail} for name, (ok, detail) in checks.items()},
    }
