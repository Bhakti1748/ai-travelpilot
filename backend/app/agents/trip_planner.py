"""
TravelPilot Trip Planner Agent
Implements the AI itinerary planning engine pipeline:
User constraints → retrieve candidates → send to LLM → generate structured itinerary → validate & auto-repair → return itinerary
"""

import datetime
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.services.constraint_engine import audit_itinerary_constraints
from app.services.dataset_service import (
    _dataset,
    haversine_distance_km,
    get_activities_for_destination,
)
from app.services.itinerary_optimizer import ItineraryOptimizer
from app.services.llm_service import default_llm_service

logger = logging.getLogger(__name__)



def _time_to_minutes(time_str: str) -> int:
    """Converts 'HH:MM' string to minutes from midnight."""
    parts = time_str.strip().split(":")
    return int(parts[0]) * 60 + int(parts[1])


def _minutes_to_time(minutes: int) -> str:
    """Converts minutes from midnight to 'HH:MM' string."""
    minutes = max(0, min(1439, minutes))
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


class ItineraryValidator:
    """
    Validates and automatically repairs an itinerary against dataset constraints:
    - Activity exists in dataset
    - Within opening and closing hours
    - No overlapping activities
    - Reasonable travel time between stops
    - Daily and trip budget limits
    """

    def __init__(
        self,
        candidates_map: Dict[str, Dict[str, Any]],
        total_budget: float,
        travelers: int = 1,
        default_travel_time_mins: int = 20,
    ):
        self.candidates_map = candidates_map
        self.total_budget = total_budget
        self.travelers = max(1, travelers)
        self.default_travel_time_mins = default_travel_time_mins

    def validate_and_repair(
        self, days: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Runs validation and auto-repairs in sequence.
        Returns: (repaired_days, list_of_repairs_made)
        """
        repairs: List[str] = []
        free_candidates = [
            act for act in self.candidates_map.values() if act.get("estimated_cost", 0) == 0
        ]
        all_candidates_list = list(self.candidates_map.values())

        for day in days:
            date_str = day.get("date", "")
            raw_activities = day.get("activities", [])
            repaired_activities = []

            for idx, act in enumerate(raw_activities):
                act_id = act.get("activity_id")

                # 1. Validate activity exists in dataset
                if act_id not in self.candidates_map:
                    # Auto-repair: Replace with an existing candidate
                    fallback = all_candidates_list[idx % len(all_candidates_list)]
                    repairs.append(
                        f"Unknown activity ID '{act_id}' replaced with real dataset venue '{fallback['id']}' ({fallback['name']})."
                    )
                    act["activity_id"] = fallback["id"]
                    act["activity_name"] = fallback["name"]
                    act["location"] = fallback["address"]
                    act["estimated_cost"] = fallback["estimated_cost"]
                    act_def = fallback
                else:
                    act_def = self.candidates_map[act_id]
                    # Ensure name, cost and location match dataset ground truth
                    act["activity_name"] = act_def["name"]
                    act["location"] = act_def["address"]
                    act["estimated_cost"] = act_def["estimated_cost"]

                # Ensure required fields
                act["date"] = date_str
                act["transportation"] = act.get("transportation") or "Metro"
                act["travel_time"] = act.get("travel_time") or f"{self.default_travel_time_mins} mins"
                act["reason"] = act.get("reason") or "Selected based on traveler interests and route efficiency."

                # 2. Validate & repair duration & times
                duration_mins = act_def.get("duration_minutes", 90)
                act["duration"] = f"{duration_mins} mins"

                start_str = act.get("start_time", "09:30")
                end_str = act.get("end_time")

                try:
                    start_mins = _time_to_minutes(start_str)
                except Exception:
                    start_mins = 9 * 60 + 30
                    start_str = "09:30"

                if not end_str:
                    end_mins = start_mins + duration_mins
                    end_str = _minutes_to_time(end_mins)
                else:
                    try:
                        end_mins = _time_to_minutes(end_str)
                        if end_mins <= start_mins:
                            end_mins = start_mins + duration_mins
                            end_str = _minutes_to_time(end_mins)
                    except Exception:
                        end_mins = start_mins + duration_mins
                        end_str = _minutes_to_time(end_mins)

                # 3. Validate & repair opening hours
                open_str = act_def.get("opening_time") or "09:00"
                close_str = act_def.get("closing_time") or "19:00"
                open_mins = _time_to_minutes(open_str)
                close_mins = _time_to_minutes(close_str)

                if start_mins < open_mins:
                    repairs.append(
                        f"Shifted '{act['activity_name']}' start from {_minutes_to_time(start_mins)} to opening time {open_str}."
                    )
                    start_mins = open_mins
                    end_mins = start_mins + duration_mins

                if end_mins > close_mins:
                    if close_mins - duration_mins >= open_mins:
                        repairs.append(
                            f"Shifted '{act['activity_name']}' earlier to fit closing time at {close_str}."
                        )
                        start_mins = close_mins - duration_mins
                        end_mins = close_mins
                    else:
                        end_mins = close_mins

                act["start_time"] = _minutes_to_time(start_mins)
                act["end_time"] = _minutes_to_time(end_mins)

                repaired_activities.append(act)

            # 4. Validate & repair overlapping times and enforce reasonable travel time
            repaired_activities.sort(key=lambda a: _time_to_minutes(a["start_time"]))

            for i in range(len(repaired_activities)):
                if i == 0:
                    continue
                prev_act = repaired_activities[i - 1]
                curr_act = repaired_activities[i]

                prev_end = _time_to_minutes(prev_act["end_time"])
                curr_start = _time_to_minutes(curr_act["start_time"])
                curr_end = _time_to_minutes(curr_act["end_time"])
                curr_duration = max(30, curr_end - curr_start)

                # Min required gap between activities (travel time)
                min_gap = self.default_travel_time_mins
                required_start = prev_end + min_gap

                if curr_start < required_start:
                    repairs.append(
                        f"Resolved overlap: Pushed '{curr_act['activity_name']}' from {_minutes_to_time(curr_start)} to {_minutes_to_time(required_start)} to allow travel buffer."
                    )
                    curr_start = required_start
                    curr_end = curr_start + curr_duration
                    curr_act["start_time"] = _minutes_to_time(curr_start)
                    curr_act["end_time"] = _minutes_to_time(curr_end)

            day["activities"] = repaired_activities

        # 5. Validate & repair total trip budget
        total_cost = sum(
            act.get("estimated_cost", 0) for d in days for act in d.get("activities", [])
        )

        if total_cost > self.total_budget:
            repairs.append(
                f"Initial itinerary cost ({total_cost:,.0f} INR) exceeded budget limit ({self.total_budget:,.0f} INR). Rebalancing high-cost activities with budget/free alternatives."
            )
            # Find expensive activities and replace with free/low cost candidates
            for day in days:
                for idx, act in enumerate(day.get("activities", [])):
                    if total_cost <= self.total_budget:
                        break
                    if act.get("estimated_cost", 0) > 2000 and free_candidates:
                        sub = free_candidates[idx % len(free_candidates)]
                        old_name = act["activity_name"]
                        old_cost = act["estimated_cost"]

                        act["activity_id"] = sub["id"]
                        act["activity_name"] = sub["name"]
                        act["location"] = sub["address"]
                        act["estimated_cost"] = sub["estimated_cost"]
                        act["reason"] = f"Substituted for budget optimization (saved {old_cost} INR)."

                        saved = old_cost - sub["estimated_cost"]
                        total_cost -= saved
                        repairs.append(
                            f"Replaced high-cost activity '{old_name}' with free scenic alternative '{sub['name']}' to stay within budget."
                        )

        return days, repairs


def _build_deterministic_itinerary(
    destination: str,
    dates: List[str],
    budget: float,
    travelers: int,
    candidates: List[Dict[str, Any]],
    travel_style: str,
    transport_preference: str,
) -> Dict[str, Any]:
    """
    Deterministic fallback itinerary generator used when Gemini API is offline or unconfigured.
    Guarantees that 100% of activity IDs come strictly from the candidate dataset.
    """
    days_result = []
    used_ids = set()

    for day_idx, date_str in enumerate(dates):
        day_num = day_idx + 1
        day_activities = []

        # Morning slot: ~09:30 - 12:00
        # Lunch slot: ~12:30 - 14:00
        # Afternoon slot: ~14:45 - 17:30
        # Evening slot: ~18:30 - 20:30

        slots = [
            {"time": "09:30", "pref_cats": ["Historical", "Museum", "Photography"]},
            {"time": "12:30", "pref_cats": ["Food", "Walking"]},
            {"time": "15:00", "pref_cats": ["Museum", "Nature", "Shopping", "Historical"]},
            {"time": "18:30", "pref_cats": ["Food", "Entertainment", "Photography"]},
        ]

        for s_idx, slot in enumerate(slots):
            # Pick best available candidate matching preferred categories
            chosen = None
            for cat in slot["pref_cats"]:
                matches = [
                    c for c in candidates
                    if c.get("category", "").lower() == cat.lower()
                    and c["id"] not in used_ids
                ]
                if matches:
                    chosen = matches[0]
                    break

            # Fallback to any unused candidate
            if not chosen:
                available = [c for c in candidates if c["id"] not in used_ids]
                if available:
                    chosen = available[0]
                else:
                    # Reuse candidates if day count is long
                    chosen = candidates[(day_idx * 4 + s_idx) % len(candidates)]

            used_ids.add(chosen["id"])

            dur_mins = chosen.get("duration_minutes", 90)
            start_mins = _time_to_minutes(slot["time"])
            end_mins = start_mins + dur_mins

            day_activities.append(
                {
                    "date": date_str,
                    "start_time": slot["time"],
                    "end_time": _minutes_to_time(end_mins),
                    "activity_id": chosen["id"],
                    "activity_name": chosen["name"],
                    "location": chosen["address"],
                    "duration": f"{dur_mins} mins",
                    "estimated_cost": chosen["estimated_cost"],
                    "travel_time": "20 mins",
                    "transportation": transport_preference,
                    "reason": f"Matches {travel_style} travel pace and destination highlights.",
                }
            )

        days_result.append(
            {
                "day_number": day_num,
                "date": date_str,
                "title": f"Day {day_num}: {destination} Highlights & Experiences",
                "activities": day_activities,
            }
        )

    return {
        "trip_title": f"Curated {travel_style} Journey in {destination}",
        "destination": destination,
        "days": days_result,
    }

def _run_destination_activity_lookup(
    destination: str,
    interests: List[str],
) -> List[Dict[str, Any]]:
    """
    Fetch activities for the requested destination using Geoapify.

    The destination service is asynchronous, while the existing
    itinerary planner is synchronous. This helper bridges the two.
    """

    import asyncio
    import concurrent.futures

    # Convert traveler interests into Geoapify categories.
    interest_category_map = {
        "museum": "museum",
        "museums": "museum",
        "history": "historical",
        "historical": "historical",
        "food": "food",
        "restaurant": "food",
        "restaurants": "food",
        "nature": "nature",
        "shopping": "shopping",
        "entertainment": "entertainment",
        "photography": "entertainment",
    }

    categories = []

    for interest in interests:
        mapped_category = interest_category_map.get(
            interest.strip().lower()
        )

        if mapped_category and mapped_category not in categories:
            categories.append(mapped_category)

    # If no recognized interests were supplied,
    # search across several useful travel categories.
    if not categories:
        categories = [
            "museum",
            "food",
            "historical",
            "nature",
            "shopping",
            "entertainment",
        ]

    async def lookup():
        return await get_activities_for_destination(
            destination=destination.strip(),
            categories=categories,
            limit=30,
        )

    # Normal case: no event loop is running.
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(lookup())

    # If an event loop is already running, use a separate
    # thread so we don't conflict with the existing loop.
    def run_in_thread():
        return asyncio.run(lookup())

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=1
    ) as executor:
        future = executor.submit(run_in_thread)
        return future.result()

def plan_itinerary(
    destination: str,
    start_date: str,
    end_date: str,
    budget: float,
    travelers: int = 1,
    interests: Optional[List[str]] = None,
    travel_style: str = "Balanced",
    transportation_preference: str = "Public Transit",
    llm_service: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Autonomous planning pipeline:
    1. Parse constraints and dates
    2. Retrieve destination-specific candidate activities from Geoapify
        with the local dataset as fallback
    3. Send candidates + constraints to LLM (with fallback)
    4. Validate itinerary constraints (no overlaps, opening hours, dataset validity, budget)
    5. Auto-repair if validation finds issues
    6. Return clean structured itinerary
    """
    service = llm_service or default_llm_service
    interests = interests or ["History", "Food", "Photography", "Museums"]

    # 1. Compute date range
    try:
        s_date = datetime.date.fromisoformat(start_date)
        e_date = datetime.date.fromisoformat(end_date)
        if e_date < s_date:
            e_date = s_date
        date_list = [
            (s_date + datetime.timedelta(days=i)).isoformat()
            for i in range((e_date - s_date).days + 1)
        ]
    except Exception:
        s_date = datetime.date.today()
        date_list = [
            (s_date + datetime.timedelta(days=i)).isoformat() for i in range(4)
        ]

    # 2. Retrieve destination-specific candidate activities
    #
    # Geoapify is used for the requested destination.
    # The existing local dataset remains as a fallback.
    try:
        all_activities = _run_destination_activity_lookup(
            destination=destination,
            interests=interests,
        )

        logger.info(
            "Retrieved %d activities for destination '%s'.",
            len(all_activities),
            destination,
        )

    except Exception as exc:
        logger.warning(
            "Geoapify activity lookup failed for '%s': %s",
            destination,
            exc,
        )

        # Preserve the existing Paris dataset as a fallback.
        all_activities = _dataset.all_activities

    if not all_activities:
        raise ValueError(
            f"No activities found for destination: {destination}"
        )

    # Match activities against traveler interests.
    #
    # Geoapify results contain their own normalized
    # "interests" field, so we use that instead of the
    # old Paris-only filter_by_interest() function.
    interest_matches = []

    normalized_interests = {
        interest.strip().lower()
        for interest in interests
    }

    for activity in all_activities:
        activity_interests = {
            str(interest).strip().lower()
            for interest in activity.get("interests", [])
        }

        activity_category = str(
            activity.get("category", "")
        ).strip().lower()

        if (
            normalized_interests.intersection(activity_interests)
            or activity_category in normalized_interests
        ):
            interest_matches.append(activity)

    if interest_matches:
        matched_ids = {
            activity["id"]
            for activity in interest_matches
        }

        candidates = interest_matches + [
            activity
            for activity in all_activities
            if activity["id"] not in matched_ids
        ]
    else:
        candidates = all_activities

    candidates_map = {
        activity["id"]: activity
        for activity in all_activities
    }

    # 3. Attempt LLM Generation
    raw_itinerary_data = None
    llm_used = False

    if service.is_configured():
        # Build concise catalog summary for Gemini
        candidates_summary = [
            {
                "id": c["id"],
                "name": c["name"],
                "category": c["category"],
                "cost": c["estimated_cost"],
                "duration_minutes": c["duration_minutes"],
                "open": c["opening_time"],
                "close": c["closing_time"],
                "address": c["address"],
                "interests": c.get("interests", []),
            }
            for c in candidates[:25]
        ]

        system_instruction = (
            "You are TravelPilot's expert AI itinerary planning engine. "
            "CRITICAL INSTRUCTION: You MUST choose activities exclusively from the provided Candidate Activities list. "
            "DO NOT invent new activity IDs. Use the exact `id`, `name`, and `address` provided. "
            "Ensure realistic start and end times, zero overlaps, and respect opening and closing hours. "
            "Return valid JSON only matching the requested schema."
        )

        prompt = f"""Plan an optimal day-by-day travel itinerary with the following constraints:

Destination: {destination}
Dates: {date_list}
Total Days: {len(date_list)}
Budget: {budget} INR
Travelers: {travelers}
Interests: {interests}
Travel Style: {travel_style}
Transportation Preference: {transportation_preference}

CANDIDATE ACTIVITIES LIST:
{json.dumps(candidates_summary, indent=2)}

OUTPUT SCHEMA:
{{
  "trip_title": "...",
  "destination": "{destination}",
  "days": [
    {{
      "day_number": 1,
      "date": "{date_list[0]}",
      "activities": [
        {{
          "date": "{date_list[0]}",
          "start_time": "09:30",
          "end_time": "12:00",
          "activity_id": "act-paris-xxx",
          "activity_name": "...",
          "location": "...",
          "duration": "150 mins",
          "estimated_cost": 2200,
          "travel_time": "20 mins",
          "transportation": "{transportation_preference}",
          "reason": "..."
        }}
      ]
    }}
  ]
}}"""

        llm_resp = service.generate_json(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.2,
        )

        if llm_resp.get("success") and llm_resp.get("data"):
            candidate_data = llm_resp["data"]
            if isinstance(candidate_data, dict) and bool(candidate_data.get("days")):
                raw_itinerary_data = candidate_data
                llm_used = True
                logger.info("Successfully received structured itinerary from Gemini.")
            else:
                logger.warning("Gemini JSON response lacked valid 'days' list; falling back to deterministic scheduler.")

    # Fallback to deterministic scheduler if LLM unconfigured or failed
    if not raw_itinerary_data:
        logger.info("Using deterministic candidate scheduler for itinerary.")
        raw_itinerary_data = _build_deterministic_itinerary(
            destination=destination,
            dates=date_list,
            budget=budget,
            travelers=travelers,
            candidates=candidates,
            travel_style=travel_style,
            transport_preference=transportation_preference,
        )

    # 4. Pipeline Execution: Generate → Validate → Optimize → Validate again → Return final itinerary
    validator = ItineraryValidator(
        candidates_map=candidates_map,
        total_budget=budget,
        travelers=travelers,
    )

    optimizer = ItineraryOptimizer(
        total_budget=budget,
        travelers=travelers,
        interests=interests,
        candidates_map=candidates_map,
    )

    # Step 1: Initial Validation & Auto-Repair
    raw_days = raw_itinerary_data.get("days", [])
    validated_days, initial_repairs = validator.validate_and_repair(raw_days)

    # Step 2: Deterministic Itinerary Optimization (geographic clustering, route smoothing, opening hours)
    optimized_days, opt_metrics = optimizer.optimize(validated_days)

    # Step 3: Second Validation & Safety Pass
    final_days, second_repairs = validator.validate_and_repair(optimized_days)

    # Step 4: Final Constraint Audit
    constraint_report = audit_itinerary_constraints(
        days=final_days,
        total_budget=budget,
        travelers=travelers,
        candidates_map=candidates_map,
    )

    all_repairs = initial_repairs + opt_metrics.get("adjustments_applied", []) + second_repairs

    total_spending = sum(
        act.get("estimated_cost", 0) for d in final_days for act in d.get("activities", [])
    ) * travelers

    return {
        "success": True,
        "trip_title": raw_itinerary_data.get("trip_title", f"{destination} Journey"),
        "destination": destination,
        "start_date": start_date,
        "end_date": end_date,
        "total_days": len(final_days),
        "total_budget": budget,
        "total_estimated_spending": total_spending,
        "remaining_budget": max(0.0, budget - total_spending),
        "travelers": travelers,
        "travel_style": travel_style,
        "transportation_preference": transportation_preference,
        "planner_engine": "Gemini 3.8 Flash" if llm_used else "Deterministic Constraint Solver",
        "validation_status": "Passed" if not all_repairs else "Auto-Repaired",
        "repairs_applied": all_repairs,
        "optimization_metrics": opt_metrics,
        "constraint_audit": {
            "is_valid": constraint_report["is_valid"],
            "total_conflicts": constraint_report["total_conflicts"],
            "has_budget_conflict": constraint_report["budget_audit"]["has_conflict"],
        },
        "days": final_days,
    }

