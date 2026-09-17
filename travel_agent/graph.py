"""Wires the agents into the LangGraph state machine.

Topology:

    START -> parse_request -> {research_hotels, research_activities} (parallel)
             -> check_constraints
                 -> (fail, retries left)  -> research_hotels  [loop, activities untouched]
                 -> (fail, retries exhausted) -> cannot_fulfill -> END
                 -> (pass) -> compose_itinerary -> approval_gate
                     -> (approved)  -> book -> END
                     -> (rejected)  -> end_unapproved -> END

check_constraints has two incoming edges (from both research nodes) but the
retry edge only targets research_hotels - verified against the installed
langgraph version that this fans in once per superstep and a selective
retry re-triggers it once without re-running the untouched branch (see
project README, "Why a hand-rolled graph, verified, not assumed").
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from travel_agent.agents.activity_agent import research_activities_node
from travel_agent.agents.approval import approval_gate_node
from travel_agent.agents.booking_agent import book_node
from travel_agent.agents.constraints import check_constraints_node
from travel_agent.agents.hotel_agent import research_hotels_node
from travel_agent.agents.itinerary import compose_itinerary_node
from travel_agent.agents.parser import parse_request_node


class TravelState(TypedDict, total=False):
    raw_query: str
    trip_request: Any
    hotel_candidates: list
    selected_hotel: dict | None
    hotel_search_calls: list
    activity_candidates: list
    selected_activities: list
    activity_search_calls: list
    constraint_report: Any
    constraint_passed: bool
    retry_count: int
    can_retry: bool
    retry_feedback: str
    itinerary: Any
    approved: bool
    booking: Any
    _tracer: Any


def _route_after_constraints(state: TravelState) -> str:
    if state.get("constraint_passed"):
        return "compose_itinerary"
    if state.get("can_retry", False):
        return "research_hotels"
    return "cannot_fulfill"


def _cannot_fulfill_node(state: TravelState) -> dict:
    return {}


def _route_after_approval(state: TravelState) -> str:
    return "book" if state.get("approved") else "end_unapproved"


def _end_unapproved_node(state: TravelState) -> dict:
    return {}


def build_graph():
    g = StateGraph(TravelState)
    g.add_node("parse_request", parse_request_node)
    g.add_node("research_hotels", research_hotels_node)
    g.add_node("research_activities", research_activities_node)
    g.add_node("check_constraints", check_constraints_node)
    g.add_node("compose_itinerary", compose_itinerary_node)
    g.add_node("cannot_fulfill", _cannot_fulfill_node)
    g.add_node("approval_gate", approval_gate_node)
    g.add_node("book", book_node)
    g.add_node("end_unapproved", _end_unapproved_node)

    g.add_edge(START, "parse_request")
    g.add_edge("parse_request", "research_hotels")
    g.add_edge("parse_request", "research_activities")
    g.add_edge("research_hotels", "check_constraints")
    g.add_edge("research_activities", "check_constraints")
    g.add_conditional_edges(
        "check_constraints",
        _route_after_constraints,
        {"compose_itinerary": "compose_itinerary", "research_hotels": "research_hotels", "cannot_fulfill": "cannot_fulfill"},
    )
    g.add_edge("cannot_fulfill", END)
    g.add_edge("compose_itinerary", "approval_gate")
    g.add_conditional_edges("approval_gate", _route_after_approval, {"book": "book", "end_unapproved": "end_unapproved"})
    g.add_edge("book", END)
    g.add_edge("end_unapproved", END)

    return g.compile(checkpointer=MemorySaver())
