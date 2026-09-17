"""Hotel search tool - plain functions, deliberately framework-agnostic.

The same function is wrapped three different ways elsewhere in this repo:
as an `@beta_tool` for the Anthropic tool runner (agents/hotel_agent.py),
and as an MCP tool (mcp_server/server.py). Keeping the core logic here and
undecorated means it's independently unit-testable and the two wrappers
can't drift apart.
"""

from __future__ import annotations

import json

from travel_agent.config import DATA_DIR

_HOTELS: list[dict] | None = None


def _load_hotels() -> list[dict]:
    global _HOTELS
    if _HOTELS is None:
        _HOTELS = json.loads((DATA_DIR / "hotels.json").read_text())
    return _HOTELS


def search_hotels(
    beachfront: bool | None = None,
    max_price_per_night_inr: int | None = None,
    cancellation_flexible: bool | None = None,
) -> list[dict]:
    """Search the hotel inventory by filters. Any filter left as None is ignored."""
    results = []
    for hotel in _load_hotels():
        if beachfront is not None and hotel["beachfront"] != beachfront:
            continue
        if max_price_per_night_inr is not None and hotel["price_per_night_inr"] > max_price_per_night_inr:
            continue
        if cancellation_flexible is not None and hotel["cancellation_flexible"] != cancellation_flexible:
            continue
        results.append(hotel)
    results.sort(key=lambda h: h["rating"], reverse=True)
    return results
