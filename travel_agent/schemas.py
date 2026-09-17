"""Pydantic schemas shared across agents, tools and evals.

These are the structured-output contracts: every LLM call that must return
something machine-usable (trip parsing, itinerary composition, judge scores)
is constrained to one of these models via `client.messages.parse`, instead
of parsing free text.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TripRequest(BaseModel):
    """Normalized form of the user's natural-language trip request."""

    destination: str
    days: int = Field(ge=1, le=30)
    travelers: int = Field(ge=1, le=20)
    budget_inr: int = Field(ge=0)
    wants_beach_hotel: bool
    sightseeing_days: int = Field(ge=0, description="Number of days to dedicate to sightseeing/activities")
    needs_flexible_cancellation: bool
    notes: str = Field(default="", description="Any other stated preference not captured by the fields above")


class HotelOption(BaseModel):
    name: str
    area: str
    price_per_night_inr: int
    rating: float
    beachfront: bool
    cancellation_flexible: bool
    amenities: list[str]


class ActivityOption(BaseModel):
    name: str
    category: str
    duration_hours: float
    price_inr: int
    description: str


class BudgetBreakdown(BaseModel):
    hotel_total_inr: int
    activities_total_inr: int
    misc_buffer_inr: int
    grand_total_inr: int
    budget_inr: int
    within_budget: bool


class ConstraintViolation(BaseModel):
    field: str
    message: str


class ConstraintReport(BaseModel):
    passed: bool
    violations: list[ConstraintViolation]
    budget: BudgetBreakdown


class DayPlan(BaseModel):
    day_number: int
    theme: str
    activities: list[str]
    notes: str = ""


class Itinerary(BaseModel):
    destination: str
    days: int
    travelers: int
    hotel: HotelOption
    day_plans: list[DayPlan]
    budget: BudgetBreakdown
    rationale: str = Field(description="Why this hotel/activity combination was chosen over the alternatives")


class JudgeScore(BaseModel):
    coherence_score: int = Field(ge=1, le=5, description="Does the day-by-day plan make geographic/logical sense?")
    preference_fit_score: int = Field(ge=1, le=5, description="Does it respect the stated preferences (beach hotel, cancellation, sightseeing)?")
    rationale: str
