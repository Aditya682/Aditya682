"""LLM-as-judge for the subjective layer predicates.py can't check:
does the day-by-day plan make geographic/logical sense, does it respect
the *spirit* of the preferences (not just the checkable fields).

Deliberately on Haiku 4.5, not the agent model - grading a structured
itinerary against a short rubric doesn't need frontier reasoning, and using
a cheaper model for judging than for generation is itself part of the
eval-cost story (see travel_agent/config.py).
"""

from __future__ import annotations

from travel_agent.config import JUDGE_MODEL
from travel_agent.llm import get_client
from travel_agent.schemas import Itinerary, JudgeScore

RUBRIC = """Score this itinerary on two dimensions, 1-5 each:

coherence_score: Does the day-by-day sequencing make sense (arrival/checkout
logistics, sightseeing not crammed back-to-back every day, activities
geographically reasonable for the chosen hotel's area)?

preference_fit_score: Does the plan actually respect what the traveler asked
for (not just the raw fields, but whether the rationale and day plans reflect
those preferences)?

Be a strict grader - a itinerary that is merely valid JSON with plausible-sounding
text should not automatically get 5s. Reserve 5 for genuinely well-reasoned plans."""


def judge_itinerary(raw_query: str, itinerary: Itinerary) -> JudgeScore:
    client = get_client()
    response = client.messages.parse(
        model=JUDGE_MODEL,
        max_tokens=512,
        system=RUBRIC,
        messages=[
            {
                "role": "user",
                "content": f"Original request:\n{raw_query}\n\nItinerary:\n{itinerary.model_dump_json(indent=2)}",
            }
        ],
        output_format=JudgeScore,
    )
    return response.parsed_output
