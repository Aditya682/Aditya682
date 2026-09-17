"""The one consequential action in the whole system - everything upstream
of this is research and planning; this is the only tool that "does"
something in the real world (a mock booking hold). The approval gate in
agents/approval.py exists specifically to sit in front of this function.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def create_booking_hold(destination: str, hotel_name: str, days: int, travelers: int, grand_total_inr: int) -> dict:
    """Place a (mock) booking hold. This is the irreversible step the
    human-in-the-loop approval gate protects."""
    return {
        "booking_id": f"HOLD-{uuid.uuid4().hex[:10].upper()}",
        "status": "confirmed",
        "destination": destination,
        "hotel_name": hotel_name,
        "days": days,
        "travelers": travelers,
        "grand_total_inr": grand_total_inr,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
