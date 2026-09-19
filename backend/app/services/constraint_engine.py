"""
TravelPilot Itinerary Constraint Engine
Detects schedule overlaps, opening hour breaches, budget overruns, travel time bottlenecks, and duplicate activities.
"""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from app.services.dataset_service import dataset_service, haversine_distance_km

logger = logging.getLogger(__name__)


def _time_to_minutes(time_str: str) -> int:
    """Parses 'HH:MM' string (e.g. '09:30' or '14:00') into minutes from midnight."""
    if not time_str:
        return 0
    clean = str(time_str).strip()
    if " " in clean:
        clean = clean.split()[0]
    parts = clean.split(":")
    hours = int(parts[0]) if parts[0].isdigit() else 0
    minutes = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return hours * 60 + minutes


def _minutes_to_time(minutes: int) -> str:
    """Converts minutes from midnight to 'HH:MM' format."""
    minutes = max(0, min(1439, minutes))
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def _parse_duration_minutes(duration_val: Any) -> int:
    """Parses durations like '150 mins', '2h 30m', or 90 to integer minutes."""
    if duration_val is None:
        return 90
    if isinstance(duration_val, (int, float)):
        return int(duration_val)
    s = str(duration_val).lower().strip()
    if s.isdigit():
        return int(s)

    total = 0
    if "h" in s:
        h_part = s.split("h")[0].strip()
        if h_part.isdigit():
            total += int(h_part) * 60
        rest = s.split("h")[1].replace("mins", "").replace("min", "").replace("m", "").strip()
        if rest.isdigit():
            total += int(rest)
    elif "m" in s:
        m_part = s.replace("mins", "").replace("min", "").replace("m", "").strip()
        if m_part.isdigit():
            total += int(m_part)
    return total if total > 0 else 90


# ----------------------------------------------------------------------
# 1. detect_time_conflicts
# ----------------------------------------------------------------------

def detect_time_conflicts(
    activities: List[Dict[str, Any]],
    min_gap_mins: int = 15,
) -> List[Dict[str, Any]]:
    """
    Detects temporal overlaps and insufficient buffers between consecutive activities on the same day.
    Supports either a flat list of activities or a list of day objects with 'activities' or 'items'.
    """
    if not activities:
        return []

    # If passed a list of day objects, audit each day individually
    if isinstance(activities[0], dict) and ("activities" in activities[0] or "items" in activities[0]):
        conflicts = []
        for day in activities:
            day_acts = day.get("activities", day.get("items", []))
            conflicts.extend(detect_time_conflicts(day_acts, min_gap_mins=min_gap_mins))
        return conflicts

    if len(activities) < 2:
        return []

    # Sort activities chronologically by start time
    sorted_acts = sorted(
        activities,
        key=lambda a: _time_to_minutes(a.get("start_time") or a.get("time", "00:00"))
    )

    conflicts = []
    for i in range(len(sorted_acts) - 1):
        cur = sorted_acts[i]
        nxt = sorted_acts[i + 1]

        cur_start = _time_to_minutes(cur.get("start_time") or cur.get("time", "00:00"))
        cur_end = _time_to_minutes(cur.get("end_time", "00:00"))
        if cur_end <= cur_start:
            dur = _parse_duration_minutes(cur.get("duration", 90))
            cur_end = cur_start + dur

        nxt_start = _time_to_minutes(nxt.get("start_time") or nxt.get("time", "00:00"))
        nxt_end = _time_to_minutes(nxt.get("end_time", "00:00"))
        if nxt_end <= nxt_start:
            dur = _parse_duration_minutes(nxt.get("duration", 90))
            nxt_end = nxt_start + dur

        # 1. Overlap: next activity starts before previous finishes
        if nxt_start < cur_end:
            overlap = cur_end - nxt_start
            desc = (
                f"Timing overlap: '{cur.get('activity_name') or cur.get('title', 'Activity 1')}' ends at {_minutes_to_time(cur_end)}, "
                f"but '{nxt.get('activity_name') or nxt.get('title', 'Activity 2')}' starts earlier at {_minutes_to_time(nxt_start)} "
                f"(overlap of {overlap} mins)."
            )
            conflicts.append({
                "type": "overlap",
                "severity": "critical",
                "activity_1": {
                    "id": cur.get("activity_id") or cur.get("id"),
                    "name": cur.get("activity_name") or cur.get("title", "Activity 1"),
                    "time": f"{_minutes_to_time(cur_start)} - {_minutes_to_time(cur_end)}",
                },
                "activity_2": {
                    "id": nxt.get("activity_id") or nxt.get("id"),
                    "name": nxt.get("activity_name") or nxt.get("title", "Activity 2"),
                    "time": f"{_minutes_to_time(nxt_start)} - {_minutes_to_time(nxt_end)}",
                },
                "overlap_minutes": overlap,
                "description": desc,
                "message": desc,
            })
        # 2. Tight connection (buffer below minimum)
        elif (nxt_start - cur_end) < min_gap_mins:
            gap = nxt_start - cur_end
            desc = (
                f"Tight connection: Only {gap}m between '{cur.get('activity_name') or cur.get('title', 'Activity 1')}' and "
                f"'{nxt.get('activity_name') or nxt.get('title', 'Activity 2')}' (minimum recommended: {min_gap_mins}m)."
            )
            conflicts.append({
                "type": "tight_buffer",
                "severity": "warning",
                "activity_1": {
                    "id": cur.get("activity_id") or cur.get("id"),
                    "name": cur.get("activity_name") or cur.get("title", "Activity 1"),
                    "time": f"{_minutes_to_time(cur_start)} - {_minutes_to_time(cur_end)}",
                },
                "activity_2": {
                    "id": nxt.get("activity_id") or nxt.get("id"),
                    "name": nxt.get("activity_name") or nxt.get("title", "Activity 2"),
                    "time": f"{_minutes_to_time(nxt_start)} - {_minutes_to_time(nxt_end)}",
                },
                "gap_minutes": gap,
                "description": desc,
                "message": desc,
            })

    return conflicts


# ----------------------------------------------------------------------
# 2. detect_opening_hour_conflicts
# ----------------------------------------------------------------------

def detect_opening_hour_conflicts(
    activities: List[Dict[str, Any]],
    candidates_map: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Detects activities scheduled outside of the venue's operating hours.
    Supports either a flat list of activities or a list of day objects with 'activities' or 'items'.
    """
    if not activities:
        return []

    # If passed a list of day objects, audit each day individually
    if isinstance(activities[0], dict) and ("activities" in activities[0] or "items" in activities[0]):
        conflicts = []
        for day in activities:
            day_acts = day.get("activities", day.get("items", []))
            conflicts.extend(detect_opening_hour_conflicts(day_acts, candidates_map=candidates_map))
        return conflicts

    conflicts = []
    for act in activities:
        act_id = act.get("activity_id") or act.get("id")
        act_name = act.get("activity_name") or act.get("title", "Activity")

        # Resolve venue data
        venue = None
        if candidates_map and act_id in candidates_map:
            venue = candidates_map[act_id]
        elif act_id:
            venue = dataset_service.get_activity(act_id)

        if not venue:
            continue

        open_str = venue.get("opening_time", "09:00")
        close_str = venue.get("closing_time", "19:00")
        open_m = _time_to_minutes(open_str)
        close_m = _time_to_minutes(close_str)

        start_str = act.get("start_time") or act.get("time", "09:30")
        end_str = act.get("end_time")
        start_m = _time_to_minutes(start_str)

        dur_m = _parse_duration_minutes(act.get("duration", venue.get("duration_minutes", 90)))
        end_m = _time_to_minutes(end_str) if end_str else (start_m + dur_m)

        # 24h open check (00:00 to 23:59 or identical)
        is_24h = (open_m == 0 and close_m >= 1439) or (open_m == close_m)
        if is_24h:
            continue

        if start_m < open_m:
            desc = f"'{act_name}' is scheduled to start at {start_str}, but venue opens at {open_str} (before opening)."
            conflicts.append({
                "activity_id": act_id,
                "activity_name": act_name,
                "type": "before_opening",
                "severity": "critical",
                "scheduled_start": start_str,
                "opening_time": open_str,
                "description": desc,
                "message": desc,
            })

        if end_m > close_m:
            desc = f"'{act_name}' ends at {_minutes_to_time(end_m)}, but venue closes at {close_str} (after closing)."
            conflicts.append({
                "activity_id": act_id,
                "activity_name": act_name,
                "type": "after_closing",
                "severity": "critical",
                "scheduled_end": _minutes_to_time(end_m),
                "closing_time": close_str,
                "description": desc,
                "message": desc,
            })

    return conflicts


# ----------------------------------------------------------------------
# 3. detect_budget_conflicts
# ----------------------------------------------------------------------

def detect_budget_conflicts(
    activities_or_days: Union[List[Dict[str, Any]], Dict[str, Any]],
    total_budget: float,
    travelers: int = 1,
) -> Dict[str, Any]:
    """
    Audits itinerary expenditure against the user's total budget constraint.
    Accepts either a flat list of activity items or a list of day objects.
    """
    travelers = max(1, travelers)
    all_acts: List[Dict[str, Any]] = []

    if isinstance(activities_or_days, list):
        for item in activities_or_days:
            if "activities" in item and isinstance(item["activities"], list):
                all_acts.extend(item["activities"])
            else:
                all_acts.append(item)
    elif isinstance(activities_or_days, dict) and "days" in activities_or_days:
        for day in activities_or_days.get("days", []):
            all_acts.extend(day.get("activities", []))

    total_cost = sum(
        float(a.get("estimated_cost", a.get("cost", 0.0))) for a in all_acts
    ) * travelers

    is_over = total_cost > total_budget
    excess = round(total_cost - total_budget, 2) if is_over else 0.0

    expensive_activities = [
        {
            "id": a.get("activity_id") or a.get("id"),
            "name": a.get("activity_name") or a.get("title"),
            "cost_per_traveler": float(a.get("estimated_cost", a.get("cost", 0.0))),
            "total_cost": float(a.get("estimated_cost", a.get("cost", 0.0))) * travelers,
        }
        for a in all_acts
        if float(a.get("estimated_cost", a.get("cost", 0.0))) > 2000
    ]
    expensive_activities.sort(key=lambda x: x["total_cost"], reverse=True)

    return {
        "has_conflict": is_over,
        "total_budget": float(total_budget),
        "total_cost": round(total_cost, 2),
        "excess_amount": excess,
        "travelers": travelers,
        "spending_percentage": round((total_cost / total_budget * 100.0) if total_budget > 0 else 0.0, 1),
        "expensive_activities": expensive_activities,
        "description": (
            f"Itinerary cost ({total_cost:,.2f} INR) exceeds budget ({total_budget:,.2f} INR) by {excess:,.2f} INR."
            if is_over
            else f"Itinerary is within budget: {total_cost:,.2f} INR spent of {total_budget:,.2f} INR."
        ),
    }


# ----------------------------------------------------------------------
# 4. detect_travel_time_conflicts
# ----------------------------------------------------------------------

def detect_travel_time_conflicts(
    activities: List[Dict[str, Any]],
    min_gap_mins: int = 15,
    candidates_map: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Evaluates geographical distance and estimated transit time between consecutive activities,
    flagging when available time between stops is less than the required transit time.
    Supports either a flat list of activities or a list of day objects with 'activities' or 'items'.
    """
    # Support candidates_map passed positionally as second argument
    if isinstance(min_gap_mins, dict) and candidates_map is None:
        candidates_map = min_gap_mins
        min_gap_mins = 15

    if not activities:
        return []

    # If passed a list of day objects, audit each day individually
    if isinstance(activities[0], dict) and ("activities" in activities[0] or "items" in activities[0]):
        conflicts = []
        for day in activities:
            day_acts = day.get("activities", day.get("items", []))
            conflicts.extend(detect_travel_time_conflicts(day_acts, min_gap_mins=min_gap_mins, candidates_map=candidates_map))
        return conflicts

    if len(activities) < 2:
        return []

    sorted_acts = sorted(
        activities,
        key=lambda a: _time_to_minutes(a.get("start_time") or a.get("time", "00:00"))
    )

    conflicts = []
    for i in range(len(sorted_acts) - 1):
        cur = sorted_acts[i]
        nxt = sorted_acts[i + 1]

        cur_id = cur.get("activity_id") or cur.get("id")
        nxt_id = nxt.get("activity_id") or nxt.get("id")

        cur_venue = (candidates_map or {}).get(cur_id) or dataset_service.get_activity(cur_id)
        nxt_venue = (candidates_map or {}).get(nxt_id) or dataset_service.get_activity(nxt_id)

        cur_lat = cur_venue.get("latitude") if cur_venue else cur.get("latitude")
        cur_lon = cur_venue.get("longitude") if cur_venue else cur.get("longitude")
        nxt_lat = nxt_venue.get("latitude") if nxt_venue else nxt.get("latitude")
        nxt_lon = nxt_venue.get("longitude") if nxt_venue else nxt.get("longitude")

        if cur_lat is None or nxt_lat is None:
            continue

        dist_km = haversine_distance_km(cur_lat, cur_lon, nxt_lat, nxt_lon)

        # Estimate realistic transit time in Paris:
        # Walking under 1.2km: ~4.5 km/h + 2 min buffer
        # Metro above 1.2km: ~22 km/h + 8 min wait/station walking
        if dist_km <= 1.2:
            req_transit_mins = max(5, round((dist_km / 4.5) * 60))
        else:
            req_transit_mins = max(12, round((dist_km / 22.0) * 60) + 8)

        cur_start = _time_to_minutes(cur.get("start_time") or cur.get("time", "00:00"))
        cur_end = _time_to_minutes(cur.get("end_time", "00:00"))
        if cur_end <= cur_start:
            dur = _parse_duration_minutes(cur.get("duration", 90))
            cur_end = cur_start + dur

        nxt_start = _time_to_minutes(nxt.get("start_time") or nxt.get("time", "00:00"))
        available_gap = nxt_start - cur_end

        if available_gap < req_transit_mins:
            deficit = req_transit_mins - available_gap
            desc = (
                f"Insufficient transit buffer between '{cur.get('activity_name') or cur.get('title', cur_id)}' and "
                f"'{nxt.get('activity_name') or nxt.get('title', nxt_id)}': distance is {dist_km} km requiring "
                f"~{req_transit_mins} mins, but only {available_gap} mins scheduled (deficit: {deficit}m)."
            )
            conflicts.append({
                "type": "travel_time_deficit",
                "severity": "critical" if available_gap <= 0 else "warning",
                "origin": cur.get("activity_name") or cur.get("title", cur_id),
                "destination": nxt.get("activity_name") or nxt.get("title", nxt_id),
                "distance_km": dist_km,
                "required_transit_minutes": req_transit_mins,
                "available_gap_minutes": available_gap,
                "deficit_minutes": deficit,
                "description": desc,
                "message": desc,
            })

    return conflicts


# ----------------------------------------------------------------------
# 5. detect_duplicate_activities
# ----------------------------------------------------------------------

def detect_duplicate_activities(days: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detects if the same activity is scheduled more than once across the entire itinerary.
    """
    seen_map: Dict[str, Dict[str, Any]] = {}
    duplicates = []

    for day in days:
        day_num = day.get("day_number", 1)
        for act in day.get("activities", []):
            act_id = act.get("activity_id") or act.get("id")
            act_name = act.get("activity_name") or act.get("title", "Unknown")

            if not act_id:
                continue

            if act_id in seen_map:
                first_seen = seen_map[act_id]
                duplicates.append({
                    "activity_id": act_id,
                    "activity_name": act_name,
                    "first_occurrence": {
                        "day_number": first_seen["day_number"],
                        "start_time": first_seen["start_time"],
                    },
                    "duplicate_occurrence": {
                        "day_number": day_num,
                        "start_time": act.get("start_time", "Unknown"),
                    },
                    "description": (
                        f"Duplicate activity: '{act_name}' ({act_id}) is scheduled on Day {first_seen['day_number']} "
                        f"and repeated on Day {day_num}."
                    ),
                })
            else:
                seen_map[act_id] = {
                    "day_number": day_num,
                    "start_time": act.get("start_time", "Unknown"),
                    "name": act_name,
                }

    return duplicates


# ----------------------------------------------------------------------
# 6. calculate_daily_cost
# ----------------------------------------------------------------------

def calculate_daily_cost(activities: List[Dict[str, Any]], travelers: int = 1) -> float:
    """
    Calculates total activity expenditure for a single day across travelers.
    """
    travelers = max(1, travelers)
    subtotal = sum(
        float(act.get("estimated_cost", act.get("cost", 0.0)))
        for act in activities
    )
    return round(subtotal * travelers, 2)


# ----------------------------------------------------------------------
# 7. calculate_total_cost
# ----------------------------------------------------------------------

def calculate_total_cost(days: List[Dict[str, Any]], travelers: int = 1) -> float:
    """
    Calculates total expenditure across all days of the itinerary.
    """
    travelers = max(1, travelers)
    total = sum(
        calculate_daily_cost(day.get("activities", []), travelers=travelers)
        for day in days
    )
    return round(total, 2)


# ----------------------------------------------------------------------
# Comprehensive Audit Runner
# ----------------------------------------------------------------------

def audit_itinerary_constraints(
    days: List[Dict[str, Any]],
    total_budget: float,
    travelers: int = 1,
    candidates_map: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Runs the full battery of constraint checks across all days of an itinerary.
    Returns a unified diagnostic report.
    """
    time_conflicts: List[Dict[str, Any]] = []
    opening_hour_conflicts: List[Dict[str, Any]] = []
    travel_time_conflicts: List[Dict[str, Any]] = []

    for day in days:
        day_acts = day.get("activities", [])
        time_conflicts.extend(detect_time_conflicts(day_acts))
        opening_hour_conflicts.extend(detect_opening_hour_conflicts(day_acts, candidates_map=candidates_map))
        travel_time_conflicts.extend(detect_travel_time_conflicts(day_acts, candidates_map=candidates_map))

    duplicate_conflicts = detect_duplicate_activities(days)
    budget_audit = detect_budget_conflicts(days, total_budget=total_budget, travelers=travelers)

    total_conflicts_count = (
        len(time_conflicts)
        + len(opening_hour_conflicts)
        + len(travel_time_conflicts)
        + len(duplicate_conflicts)
        + (1 if budget_audit["has_conflict"] else 0)
    )

    return {
        "is_valid": total_conflicts_count == 0,
        "total_conflicts": total_conflicts_count,
        "time_conflicts": time_conflicts,
        "opening_hour_conflicts": opening_hour_conflicts,
        "travel_time_conflicts": travel_time_conflicts,
        "duplicate_conflicts": duplicate_conflicts,
        "budget_audit": budget_audit,
        "total_calculated_cost": calculate_total_cost(days, travelers=travelers),
    }
