"""Exposes the same tools the agents use as an MCP server, so any MCP
client (Claude Desktop, another agent, etc.) can drive the underlying
travel-search backend directly - not just this project's own graph.

Deliberately thin: every handler below just calls the plain functions in
travel_agent/tools/, the same ones agents/hotel_agent.py and
agents/activity_agent.py wrap as Anthropic tool-runner tools. One
implementation, two callers, so the MCP surface can't drift from what the
in-process agents actually do.

Run with:
    python -m mcp_server.server
Or point an MCP client's config at this module with stdio transport.
"""

from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer

from travel_agent.rag import retrieve_context
from travel_agent.tools.activity_search import search_activities
from travel_agent.tools.constraint_check import check_constraints
from travel_agent.tools.hotel_search import search_hotels

mcp = MCPServer("goa-travel-planner")


@mcp.tool()
def find_hotels(
    beachfront: bool | None = None,
    max_price_per_night_inr: int | None = None,
    cancellation_flexible: bool | None = None,
) -> str:
    """Search the Goa hotel inventory. Leave any filter as null to ignore it."""
    return json.dumps(
        search_hotels(
            beachfront=beachfront,
            max_price_per_night_inr=max_price_per_night_inr,
            cancellation_flexible=cancellation_flexible,
        )
    )


@mcp.tool()
def find_activities(category: str | None = None, max_price_inr: int | None = None) -> str:
    """Search Goa activities/sightseeing options. category is one of
    "sightseeing", "leisure", "adventure", or null for all."""
    return json.dumps(search_activities(category=category, max_price_inr=max_price_inr))


@mcp.tool()
def check_trip_budget(
    hotel_name: str,
    activity_names: list[str],
    days: int,
    travelers: int,
    budget_inr: int,
    needs_flexible_cancellation: bool = False,
    wants_beach_hotel: bool = False,
) -> str:
    """Check whether a specific hotel + activity combination fits the stated
    budget and preferences. hotel_name/activity_names must match names
    returned by find_hotels/find_activities."""
    hotels = {h["name"]: h for h in search_hotels()}
    activities = {a["name"]: a for a in search_activities()}
    if hotel_name not in hotels:
        return json.dumps({"error": f"Unknown hotel: {hotel_name}"})
    chosen_activities = [activities[n] for n in activity_names if n in activities]

    report = check_constraints(
        hotel=hotels[hotel_name],
        activities=chosen_activities,
        days=days,
        travelers=travelers,
        budget_inr=budget_inr,
        needs_flexible_cancellation=needs_flexible_cancellation,
        wants_beach_hotel=wants_beach_hotel,
    )
    return report.model_dump_json()


@mcp.tool()
def goa_area_guide(question: str) -> str:
    """Answer a question about Goa's areas, distances or cancellation
    policies using the local knowledge base (retrieval-augmented)."""
    return retrieve_context(question, k=3)


if __name__ == "__main__":
    mcp.run()
