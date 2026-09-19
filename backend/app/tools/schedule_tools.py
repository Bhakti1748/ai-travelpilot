"""
Schedule Tools for TravelPilot Agent.
Includes check_opening_hours and detect_schedule_conflicts.
"""

from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.database.session import SessionLocal
from app.models.db_models import ItineraryItemModel, TripModel
from app.services.dataset_service import dataset_service, haversine_distance_km
from app.tools.registry import default_tool_registry

logger = logging.getLogger(__name__)


def _parse_time_to_minutes(time_str: str) -> int:
    """Parses 'HH:MM' string to minutes from midnight."""
    clean = time_str.strip()
    # Handle "09:00 AM" or "9:00"
    if " " in clean:
        clean = clean.split()[0]
    parts = clean.split(":")
    hours = int(parts[0])
    minutes = int(parts[1]) if len(parts) > 1 else 0
    return hours * 60 + minutes


def _parse_duration_to_minutes(duration_str: str) -> int:
    """Parses strings like '1h 30m', '2h', '45m', or '90' to minutes."""
    if not duration_str:
        return 60
    clean = str(duration_str).lower().strip()
    if clean.isdigit():
        return int(clean)
    
    total = 0
    if "h" in clean:
        h_part = clean.split("h")[0].strip()
        if h_part.isdigit():
            total += int(h_part) * 60
        rest = clean.split("h")[1].replace("m", "").strip()
        if rest.isdigit():
            total += int(rest)
    elif "m" in clean:
        m_part = clean.replace("m", "").strip()
        if m_part.isdigit():
            total += int(m_part)
    else:
        total = 60
    return total if total > 0 else 60


# ----------------------------------------------------------------------
# Tool 6: check_opening_hours
# ----------------------------------------------------------------------

class CheckOpeningHoursInput(BaseModel):
    activity_id: str = Field(..., description="Unique ID of the activity (e.g. 'act-paris-001')")
    time: str = Field(..., description="Planned visit time in 24-hour 'HH:MM' format (e.g. '10:30')")
    duration_minutes: Optional[int] = Field(None, description="Expected duration in minutes to verify visit finishes before closing")


class CheckOpeningHoursOutput(BaseModel):
    activity_id: str
    activity_name: str
    requested_time: str
    is_open: bool
    fits_duration: bool
    opening_time: str
    closing_time: str
    status: str
    message: str
    minutes_until_close: Optional[int] = None


def check_opening_hours(
    activity_id: str,
    time: str,
    duration_minutes: Optional[int] = None
) -> Dict[str, Any]:
    """
    Checks if a target activity is open at the specified time and if the visit fits within operating hours.
    """
    activity = dataset_service.get_activity(activity_id)
    if not activity:
        return {
            "activity_id": activity_id,
            "activity_name": "Unknown",
            "requested_time": time,
            "is_open": False,
            "fits_duration": False,
            "opening_time": "Unknown",
            "closing_time": "Unknown",
            "status": "not_found",
            "message": f"Activity '{activity_id}' not found in dataset.",
            "minutes_until_close": None,
        }

    opening_time = activity.get("opening_time", "09:00")
    closing_time = activity.get("closing_time", "18:00")
    act_name = activity.get("name", activity_id)
    default_duration = activity.get("duration_minutes", 60)
    dur = duration_minutes if duration_minutes is not None else default_duration

    req_mins = _parse_time_to_minutes(time)
    open_mins = _parse_time_to_minutes(opening_time)
    close_mins = _parse_time_to_minutes(closing_time)

    # 24-hour open places (e.g. 00:00 to 23:59 or equal)
    is_24h = (open_mins == 0 and close_mins >= 1439) or (open_mins == close_mins)
    
    if is_24h:
        is_open = True
        fits_duration = True
        mins_left = 1440 - req_mins
        status = "open"
        msg = f"{act_name} is open 24 hours."
    elif open_mins <= req_mins < close_mins:
        is_open = True
        mins_left = close_mins - req_mins
        if mins_left >= dur:
            fits_duration = True
            status = "open"
            msg = f"{act_name} is open at {time}. Operating hours: {opening_time} - {closing_time} ({mins_left} mins remaining)."
        else:
            fits_duration = False
            status = "closing_soon"
            msg = (
                f"{act_name} is open at {time} but closes at {closing_time}. "
                f"Planned duration ({dur}m) exceeds remaining open time ({mins_left}m)."
            )
    else:
        is_open = False
        fits_duration = False
        mins_left = 0
        status = "closed"
        if req_mins < open_mins:
            msg = f"{act_name} opens at {opening_time}. Scheduled time {time} is too early."
        else:
            msg = f"{act_name} closed at {closing_time}. Scheduled time {time} is after closing."

    return {
        "activity_id": activity_id,
        "activity_name": act_name,
        "requested_time": time,
        "is_open": is_open,
        "fits_duration": fits_duration,
        "opening_time": opening_time,
        "closing_time": closing_time,
        "status": status,
        "message": msg,
        "minutes_until_close": mins_left,
    }


default_tool_registry.register(
    name="check_opening_hours",
    description="Verify whether an activity is open at a given time ('HH:MM') and whether the planned visit duration fits before closing.",
    parameters_schema=CheckOpeningHoursInput.model_json_schema(),
    func=check_opening_hours,
    input_model=CheckOpeningHoursInput,
)


# ----------------------------------------------------------------------
# Tool 9: detect_schedule_conflicts
# ----------------------------------------------------------------------

class DetectScheduleConflictsInput(BaseModel):
    trip_id: str = Field(..., description="Unique trip identifier (e.g. 'trip-paris-demo-2026')")
    day_number: Optional[int] = Field(None, description="Optional specific day to inspect (1-indexed). If omitted, scans all days.")
    min_buffer_minutes: int = Field(15, description="Minimum recommended buffer minutes between consecutive activities for travel/rest.")


def detect_schedule_conflicts(
    trip_id: str,
    day_number: Optional[int] = None,
    min_buffer_minutes: int = 15,
) -> Dict[str, Any]:
    """
    Scans a trip's itinerary items for schedule overlaps and insufficient transit buffers between consecutive activities.
    """
    db = SessionLocal()
    try:
        trip = db.query(TripModel).filter(TripModel.id == trip_id).first()
        if not trip:
            return {
                "trip_id": trip_id,
                "conflicts_found": False,
                "total_conflicts": 0,
                "conflicts": [],
                "recommendations": [f"Trip '{trip_id}' not found in database."],
            }

        query = db.query(ItineraryItemModel).filter(ItineraryItemModel.trip_id == trip_id)
        if day_number is not None:
            query = query.filter(ItineraryItemModel.day_number == day_number)
        
        items = query.order_by(ItineraryItemModel.day_number, ItineraryItemModel.order, ItineraryItemModel.time).all()
        
        # Group items by day
        days_map: Dict[int, List[ItineraryItemModel]] = {}
        for item in items:
            days_map.setdefault(item.day_number, []).append(item)

        conflicts: List[Dict[str, Any]] = []
        recommendations: List[str] = []

        for day, day_items in sorted(days_map.items()):
            # Sort chronologically by start minutes
            parsed_day_items = []
            for itm in day_items:
                start_m = _parse_time_to_minutes(itm.time)
                dur_m = _parse_duration_to_minutes(itm.duration)
                end_m = start_m + dur_m
                parsed_day_items.append({
                    "id": itm.id,
                    "title": itm.title,
                    "start_time": itm.time,
                    "duration": itm.duration,
                    "start_m": start_m,
                    "end_m": end_m,
                    "location": itm.location or "",
                    "day_number": day,
                })

            parsed_day_items.sort(key=lambda x: x["start_m"])

            for i in range(len(parsed_day_items) - 1):
                cur = parsed_day_items[i]
                nxt = parsed_day_items[i + 1]

                # 1. Direct overlap: next starts before current finishes
                if nxt["start_m"] < cur["end_m"]:
                    overlap_m = cur["end_m"] - nxt["start_m"]
                    conflicts.append({
                        "day_number": day,
                        "type": "overlap",
                        "severity": "critical",
                        "item_1": {"id": cur["id"], "title": cur["title"], "time": cur["start_time"]},
                        "item_2": {"id": nxt["id"], "title": nxt["title"], "time": nxt["start_time"]},
                        "overlap_minutes": overlap_m,
                        "description": (
                            f"Day {day} direct overlap: '{cur['title']}' ends after '{nxt['title']}' starts "
                            f"by {overlap_m} minutes."
                        ),
                    })
                    recommendations.append(
                        f"Reschedule '{nxt['title']}' to start after {_format_minutes(cur['end_m'] + min_buffer_minutes)} on Day {day}."
                    )
                # 2. Insufficient buffer: gap is positive but less than minimum buffer
                elif nxt["start_m"] - cur["end_m"] < min_buffer_minutes:
                    gap_m = nxt["start_m"] - cur["end_m"]
                    conflicts.append({
                        "day_number": day,
                        "type": "insufficient_buffer",
                        "severity": "warning",
                        "item_1": {"id": cur["id"], "title": cur["title"], "time": cur["start_time"]},
                        "item_2": {"id": nxt["id"], "title": nxt["title"], "time": nxt["start_time"]},
                        "buffer_minutes": gap_m,
                        "description": (
                            f"Day {day} tight connection: Only {gap_m}m buffer between '{cur['title']}' "
                            f"and '{nxt['title']}' (recommended: at least {min_buffer_minutes}m)."
                        ),
                    })
                    recommendations.append(
                        f"Add at least {min_buffer_minutes - gap_m}m buffer between '{cur['title']}' and '{nxt['title']}' on Day {day}."
                    )

        return {
            "trip_id": trip_id,
            "conflicts_found": len(conflicts) > 0,
            "total_conflicts": len(conflicts),
            "conflicts": conflicts,
            "recommendations": recommendations if recommendations else ["Itinerary schedule is well-spaced with no detected conflicts."],
        }
    finally:
        db.close()


def _format_minutes(minutes: int) -> str:
    """Helper to convert minutes from midnight to 'HH:MM' string."""
    h = (minutes // 60) % 24
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


default_tool_registry.register(
    name="detect_schedule_conflicts",
    description="Analyze a trip's itinerary for timing overlaps and tight connection buffers between scheduled activities.",
    parameters_schema=DetectScheduleConflictsInput.model_json_schema(),
    func=detect_schedule_conflicts,
    input_model=DetectScheduleConflictsInput,
)
