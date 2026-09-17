"""Activity/sightseeing search tool - same pattern as hotel_search.py."""

from __future__ import annotations

import json

from travel_agent.config import DATA_DIR

_ACTIVITIES: list[dict] | None = None


def _load_activities() -> list[dict]:
    global _ACTIVITIES
    if _ACTIVITIES is None:
        _ACTIVITIES = json.loads((DATA_DIR / "activities.json").read_text())
    return _ACTIVITIES


def search_activities(
    category: str | None = None,
    max_price_inr: int | None = None,
) -> list[dict]:
    """Search activities/sightseeing options. category one of:
    sightseeing, leisure, adventure. Leave a filter as None to ignore it."""
    results = []
    for activity in _load_activities():
        if category is not None and activity["category"] != category:
            continue
        if max_price_inr is not None and activity["price_inr"] > max_price_inr:
            continue
        results.append(activity)
    return results
