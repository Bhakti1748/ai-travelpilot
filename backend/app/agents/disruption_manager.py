"""
TravelPilot Disruption Manager & Automatic Replanning Agent

Implements the autonomous disruption-resolution workflow:

1. Retrieve current trip state
2. Identify directly affected itinerary items
3. Identify downstream impacts
4. Find destination-aware candidate alternatives
5. Multi-constraint scoring
6. Rank alternatives & select recommendation
7. Rebuild affected itinerary portion
8. Run constraint validation
9. Run itinerary optimization
10. Return structured response

Important:
- Live destinations use Geoapify-backed activity search.
- The disruption manager does NOT use the Paris dataset as a fallback
  for live destinations.
- Existing Paris data can still be used when the actual trip destination
  is Paris.
"""

import asyncio
import copy
import datetime
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.db_models import (
    BookingModel,
    BudgetModel,
    DisruptionModel,
    ItineraryItemModel,
    TripModel,
)
from app.services.constraint_engine import (
    _minutes_to_time,
    _parse_duration_minutes,
    _time_to_minutes,
    audit_itinerary_constraints,
    calculate_total_cost,
)
from app.services.dataset_service import (
    dataset_service,
    haversine_distance_km,
)
from app.services.itinerary_optimizer import ItineraryOptimizer

logger = logging.getLogger(__name__)


class DisruptionManager:
    """
    Autonomous agent handling travel disruption detection,
    simulation, and replanning.
    """

    def __init__(self, db: Optional[Session] = None):
        self._external_db = db

    def _get_db(self) -> Session:
        return (
            self._external_db
            if self._external_db is not None
            else SessionLocal()
        )

    # ------------------------------------------------------------------
    # Utility: Run async code from the synchronous disruption workflow
    # ------------------------------------------------------------------
    def _run_async(self, coroutine):
        """
        Runs an async coroutine while keeping the public disruption
        manager methods synchronous.

        This allows the existing FastAPI routes to continue calling:
            manager.simulate_disruption(...)
            manager.replan_and_apply(...)

        without requiring API route changes.
        """

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop.
            return asyncio.run(coroutine)

        # If a loop is already running in this thread, execute the
        # coroutine in a separate thread.
        import concurrent.futures

        def runner():
            return asyncio.run(coroutine)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(runner)
            return future.result()

    # ------------------------------------------------------------------
    # Step 1: Retrieve Current Trip State
    # ------------------------------------------------------------------
    def get_trip_state(
        self,
        trip_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """Loads trip, items, budget, and bookings from database."""

        trip = (
            db.query(TripModel)
            .filter(TripModel.id == trip_id)
            .first()
        )

        if not trip:
            raise ValueError(
                f"Trip '{trip_id}' does not exist."
            )

        items = (
            db.query(ItineraryItemModel)
            .filter(ItineraryItemModel.trip_id == trip_id)
            .order_by(
                ItineraryItemModel.day_number,
                ItineraryItemModel.order,
                ItineraryItemModel.time,
            )
            .all()
        )

        bookings = (
            db.query(BookingModel)
            .filter(BookingModel.trip_id == trip_id)
            .all()
        )

        budget_rec = (
            db.query(BudgetModel)
            .filter(BudgetModel.trip_id == trip_id)
            .first()
        )

        interests = []

        if trip.interests:
            try:
                interests = json.loads(trip.interests)
            except Exception:
                interests = [
                    i.strip()
                    for i in trip.interests.split(",")
                    if i.strip()
                ]

        # Group itinerary items by day.
        days_dict: Dict[int, List[Dict[str, Any]]] = {}

        for item in items:
            days_dict.setdefault(
                item.day_number,
                [],
            ).append(
                {
                    "id": item.id,
                    "trip_id": item.trip_id,
                    "day_number": item.day_number,
                    "date": item.date,
                    "start_time": item.time,
                    "end_time": self._estimate_end_time(
                        item.time,
                        item.duration,
                    ),
                    "activity_name": item.title,
                    "activity_id": self._resolve_activity_id(
                        item.title,
                        item.location,
                    ),
                    "category": item.category,
                    "duration": item.duration,
                    "location": item.location,
                    "cost": item.cost,
                    "estimated_cost": item.cost,
                    "currency": item.currency or trip.currency,
                    "transportation": (
                        item.transportation
                        or "Metro"
                    ),
                    "status": item.status,
                    "notes": item.notes or "",
                    "order": item.order,
                    "is_booking": False,
                }
            )

        # Inject confirmed bookings.
        for booking in bookings:
            b_day = 1

            days_dict.setdefault(
                b_day,
                [],
            ).append(
                {
                    "id": booking.id,
                    "trip_id": booking.trip_id,
                    "day_number": b_day,
                    "date": trip.start_date,
                    "start_time": (
                        booking.start_time.split()[-1]
                        if booking.start_time
                        and " " in booking.start_time
                        else (
                            booking.start_time
                            or "14:00"
                        )
                    ),
                    "end_time": (
                        booking.end_time.split()[-1]
                        if booking.end_time
                        and " " in booking.end_time
                        else (
                            booking.end_time
                            or "16:00"
                        )
                    ),
                    "activity_name": (
                        f"{booking.booking_type}: "
                        f"{booking.title}"
                    ),
                    "category": booking.booking_type,
                    "duration": "120 mins",
                    "location": booking.provider,
                    "cost": booking.cost,
                    "estimated_cost": booking.cost,
                    "currency": (
                        booking.currency
                        or trip.currency
                    ),
                    "transportation": (
                        "Taxi"
                        if booking.booking_type == "Flight"
                        else "Metro"
                    ),
                    "status": booking.status,
                    "notes": (
                        f"Confirmed booking "
                        f"({booking.reference_code})"
                    ),
                    "order": 99,
                    "is_booking": True,
                }
            )

        days_list = []

        for day_number in sorted(days_dict.keys()):
            day_items = sorted(
                days_dict[day_number],
                key=lambda x: _time_to_minutes(
                    x["start_time"]
                ),
            )

            days_list.append(
                {
                    "day_number": day_number,
                    "date": (
                        day_items[0]["date"]
                        if day_items
                        else trip.start_date
                    ),
                    "activities": day_items,
                }
            )

        return {
            "trip": trip,
            "trip_id": trip.id,
            "destination": trip.destination,
            "budget": trip.budget,
            "spending": trip.spending,
            "travelers": trip.travelers,
            "interests": interests,
            "currency": trip.currency,
            "days": days_list,
            "raw_items": items,
            "bookings": bookings,
            "budget_record": budget_rec,
        }

    def _estimate_end_time(
        self,
        start_time: str,
        duration: Optional[str],
    ) -> str:
        start_minutes = _time_to_minutes(start_time)

        duration_minutes = _parse_duration_minutes(
            duration or "90 mins"
        )

        return _minutes_to_time(
            start_minutes + duration_minutes
        )

    # ------------------------------------------------------------------
    # Activity ID Resolution
    # ------------------------------------------------------------------
    def _resolve_activity_id(
        self,
        title: str,
        location: Optional[str],
    ) -> str:
        """
        Attempts to match an itinerary activity with the local catalog.

        Important:
        Never returns a fake Paris activity ID.

        Dynamic Geoapify activities may not exist in the local catalog.
        In that case we return an empty string and allow title/location
        matching to handle the itinerary item.
        """

        title_lower = (title or "").lower().strip()

        if not title_lower:
            return ""

        try:
            for activity in dataset_service.all_activities:
                activity_name = str(
                    activity.get("name", "")
                ).lower()

                if (
                    activity_name
                    and (
                        activity_name in title_lower
                        or title_lower in activity_name
                    )
                ):
                    return activity.get("id", "")

            # Partial word matching.
            words = [
                word
                for word in title_lower.split()
                if len(word) > 4
            ]

            for activity in dataset_service.all_activities:
                activity_name = str(
                    activity.get("name", "")
                ).lower()

                if any(
                    word in activity_name
                    for word in words
                ):
                    return activity.get("id", "")

        except Exception as exc:
            logger.warning(
                "Activity ID resolution failed: %s",
                exc,
            )

        # IMPORTANT:
        # Do not use "act-paris-001" or any other hardcoded ID.
        return ""

    # ------------------------------------------------------------------
    # Step 2: Identify Directly Affected Items
    # ------------------------------------------------------------------
    def identify_affected_items(
        self,
        days: List[Dict[str, Any]],
        disruption_type: str,
        activity_id: Optional[str] = None,
        title: Optional[str] = None,
        time: Optional[str] = None,
        day_number: Optional[int] = None,
        new_interests: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Finds itinerary items directly affected by a disruption."""

        affected = []

        target_name = (
            title or ""
        ).lower().strip()

        target_id = (
            activity_id or ""
        ).strip()

        for day in days:
            current_day = day.get(
                "day_number",
                1,
            )

            if (
                day_number is not None
                and current_day != day_number
            ):
                continue

            for activity in day.get(
                "activities",
                [],
            ):
                match = False

                activity_id_value = (
                    activity.get("activity_id")
                    or ""
                )

                activity_record_id = (
                    activity.get("id")
                    or ""
                )

                activity_name = (
                    activity.get("activity_name")
                    or activity.get("title")
                    or ""
                ).lower()

                if target_id and (
                    activity_id_value == target_id
                    or activity_record_id == target_id
                ):
                    match = True

                elif target_name and (
                    target_name in activity_name
                    or activity_name in target_name
                ):
                    match = True

                elif (
                    time
                    and activity.get("start_time") == time
                    and (
                        day_number is None
                        or current_day == day_number
                    )
                ):
                    match = True

                if match:
                    affected.append(
                        dict(activity)
                    )

        # Budget disruptions:
        # select the highest-cost non-booking activities.
        if (
            not affected
            and disruption_type
            in (
                "budget_reduced",
                "budget",
            )
        ):
            all_activities = [
                activity
                for day in days
                for activity in day.get(
                    "activities",
                    [],
                )
                if not activity.get("is_booking")
            ]

            all_activities.sort(
                key=lambda x: float(
                    x.get(
                        "cost",
                        x.get(
                            "estimated_cost",
                            0.0,
                        ),
                    )
                    or 0.0
                ),
                reverse=True,
            )

            if all_activities:
                affected = all_activities[:2]

        # Interest changes:
        # identify an activity that no longer matches.
        if (
            not affected
            and disruption_type
            in (
                "user_interests_changed",
                "interests_changed",
            )
        ):
            target_interests = [
                str(interest).lower()
                for interest in (
                    new_interests or []
                )
            ]

            for day in days:
                for activity in day.get(
                    "activities",
                    [],
                ):
                    if activity.get("is_booking"):
                        continue

                    category = (
                        activity.get(
                            "category",
                            "",
                        )
                        or ""
                    ).lower()

                    if not any(
                        interest in category
                        or category in interest
                        for interest in target_interests
                    ):
                        affected.append(
                            dict(activity)
                        )
                        break

                if affected:
                    break

        return affected

    # ------------------------------------------------------------------
    # Step 3: Identify Downstream Impacts
    # ------------------------------------------------------------------
    def identify_downstream_impacts(
        self,
        days: List[Dict[str, Any]],
        affected_items: List[Dict[str, Any]],
        disruption_type: str,
        delay_minutes: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Identifies subsequent activities impacted by timing
        cascades or schedule voids.
        """

        downstream = []

        affected_ids = {
            activity.get("id")
            for activity in affected_items
        }

        for day in days:
            day_activities = day.get(
                "activities",
                [],
            )

            for index, activity in enumerate(
                day_activities
            ):
                if activity.get("id") in affected_ids:

                    subsequent = (
                        day_activities[index + 1 :]
                    )

                    for following_activity in subsequent:
                        downstream.append(
                            {
                                "item": dict(
                                    following_activity
                                ),
                                "day_number": day.get(
                                    "day_number"
                                ),
                                "impact_type": (
                                    "timing_shift"
                                    if delay_minutes > 0
                                    else "transit_buffer_gap"
                                ),
                                "delay_cascade_minutes": (
                                    delay_minutes
                                ),
                                "description": (
                                    (
                                        f"Will require "
                                        f"{_minutes_to_time(_time_to_minutes(following_activity.get('start_time', '00:00')) + delay_minutes)} "
                                        f"timing push due to preceding delay."
                                    )
                                    if delay_minutes > 0
                                    else (
                                        "Schedule window opened "
                                        "up after preceding "
                                        "activity cancellation."
                                    )
                                ),
                            }
                        )

                    break

        return downstream

    # ------------------------------------------------------------------
    # Step 4, 5, 6:
    # Destination-Aware Candidate Alternatives
    # ------------------------------------------------------------------
    async def _generate_candidate_alternatives_async(
        self,
        target_item: Dict[str, Any],
        trip_interests: List[str],
        used_activity_ids: List[str],
        destination: str,
        max_cost: Optional[float] = None,
        limit: int = 4,
    ) -> Tuple[
        List[Dict[str, Any]],
        Optional[Dict[str, Any]],
    ]:
        """
        Finds alternative activities for the actual trip destination.

        Geoapify is used through dataset_service.

        No hardcoded Paris coordinates are used.
        No global Paris catalog is merged into live destinations.
        """

        if not isinstance(target_item, dict):
            target_item = {}

        target_activity_id = (
            target_item.get("activity_id")
            or ""
        )

        target_title = (
            target_item.get("activity_name")
            or target_item.get("title")
            or ""
        )

        target_category = (
            target_item.get("category")
            or ""
        )

        target_time = (
            target_item.get("start_time")
            or target_item.get("time")
            or "10:00"
        )

        target_time_minutes = _time_to_minutes(
            target_time
        )

        target_duration_minutes = (
            _parse_duration_minutes(
                target_item.get("duration")
                or "90 mins"
            )
        )

        # --------------------------------------------------------------
        # Search categories
        # --------------------------------------------------------------
        categories = []

        if target_category:
            categories.append(
                str(target_category).strip()
            )

        # Add useful generic categories.
        categories.extend(
            [
                "museum",
                "food",
                "historical",
                "nature",
                "shopping",
                "entertainment",
            ]
        )

        # Remove duplicates while preserving order.
        unique_categories = []

        for category in categories:
            normalized = str(
                category
            ).strip().lower()

            if (
                normalized
                and normalized not in unique_categories
            ):
                unique_categories.append(
                    normalized
                )

        # --------------------------------------------------------------
        # Fetch activities from the actual destination.
        # --------------------------------------------------------------
        try:
            destination_activities = (
                await dataset_service.get_activities_for_destination(
                    destination=destination,
                    categories=unique_categories,
                    limit=40,
                )
            )

        except Exception as exc:
            logger.error(
                "Destination activity search failed for '%s': %s",
                destination,
                exc,
            )
            destination_activities = []

        if not destination_activities:
            logger.warning(
                "No destination-local alternatives found for '%s'.",
                destination,
            )

            return [], None

        # --------------------------------------------------------------
        # Build candidate pool.
        # --------------------------------------------------------------
        candidate_pool: Dict[
            str,
            Dict[str, Any],
        ] = {}

        destination_lower = (
            destination or ""
        ).lower()

        is_paris_trip = (
            "paris" in destination_lower
        )

        for activity in destination_activities:

            activity_id = (
                activity.get("id")
                or activity.get("activity_id")
            )

            if not activity_id:
                continue

            # If Geoapify failed and dataset_service returned
            # a Paris fallback for another destination, reject it.
            if (
                not is_paris_trip
                and str(activity_id).startswith(
                    "act-paris-"
                )
            ):
                continue

            activity_name = str(
                activity.get(
                    "name",
                    "",
                )
            ).strip()

            # Never recommend the same activity.
            if (
                target_activity_id
                and activity_id == target_activity_id
            ):
                continue

            # Avoid exact title duplicate.
            if (
                target_title
                and activity_name
                and activity_name.lower()
                == target_title.lower()
            ):
                continue

            if activity_id in used_activity_ids:
                continue

            candidate_pool[
                activity_id
            ] = activity

        if not candidate_pool:
            logger.warning(
                "No valid destination-local alternatives remain "
                "after filtering for '%s'.",
                destination,
            )

            return [], None

        # --------------------------------------------------------------
        # Resolve target coordinates.
        #
        # First try the target activity itself.
        # Then search the fetched destination activities by title.
        # --------------------------------------------------------------
        target_activity = None

        if target_activity_id:
            try:
                target_activity = (
                    dataset_service.get_activity(
                        target_activity_id
                    )
                )
            except Exception:
                target_activity = None

        if not target_activity and target_title:
            target_title_lower = (
                target_title.lower()
            )

            for activity in destination_activities:
                name = str(
                    activity.get(
                        "name",
                        "",
                    )
                ).lower()

                if (
                    name == target_title_lower
                    or name in target_title_lower
                    or target_title_lower in name
                ):
                    target_activity = activity
                    break

        ref_lat = None
        ref_lon = None

        if target_activity:
            ref_lat = target_activity.get(
                "latitude"
            )
            ref_lon = target_activity.get(
                "longitude"
            )

        if ref_lat is None:
            ref_lat = target_item.get(
                "latitude"
            )

        if ref_lon is None:
            ref_lon = target_item.get(
                "longitude"
            )

        # --------------------------------------------------------------
        # Interests
        # --------------------------------------------------------------
        interests_set = {
            str(interest).strip().lower()
            for interest in (
                trip_interests or []
            )
            if str(interest).strip()
        }

        candidates_scored = []

        # --------------------------------------------------------------
        # Score candidates.
        # --------------------------------------------------------------
        for activity_id, candidate in (
            candidate_pool.items()
        ):

            # Cost.
            try:
                cost = float(
                    candidate.get(
                        "estimated_cost",
                        0.0,
                    )
                    or 0.0
                )
            except (
                TypeError,
                ValueError,
            ):
                cost = 0.0

            if (
                max_cost is not None
                and cost > max_cost
            ):
                continue

            # ----------------------------------------------------------
            # Coordinates / distance
            # ----------------------------------------------------------
            candidate_lat = candidate.get(
                "latitude"
            )

            candidate_lon = candidate.get(
                "longitude"
            )

            if (
                ref_lat is not None
                and ref_lon is not None
                and candidate_lat is not None
                and candidate_lon is not None
            ):
                try:
                    distance_km = (
                        haversine_distance_km(
                            float(ref_lat),
                            float(ref_lon),
                            float(candidate_lat),
                            float(candidate_lon),
                        )
                    )
                except Exception:
                    distance_km = None
            else:
                distance_km = None

            # ----------------------------------------------------------
            # Opening hours
            # ----------------------------------------------------------
            opening_minutes = _time_to_minutes(
                candidate.get(
                    "opening_time"
                )
                or "09:00"
            )

            closing_minutes = _time_to_minutes(
                candidate.get(
                    "closing_time"
                )
                or "19:00"
            )

            is_24_hours = (
                (
                    opening_minutes == 0
                    and closing_minutes >= 1439
                )
                or opening_minutes
                == closing_minutes
            )

            hours_compatible = (
                is_24_hours
                or (
                    opening_minutes
                    <= target_time_minutes
                    and (
                        target_time_minutes
                        + target_duration_minutes
                    )
                    <= closing_minutes
                )
            )

            # ----------------------------------------------------------
            # Duration
            # ----------------------------------------------------------
            try:
                candidate_duration = int(
                    candidate.get(
                        "duration_minutes",
                        90,
                    )
                    or 90
                )
            except (
                TypeError,
                ValueError,
            ):
                candidate_duration = 90

            duration_difference = abs(
                candidate_duration
                - target_duration_minutes
            )

            # ----------------------------------------------------------
            # Interests
            # ----------------------------------------------------------
            candidate_interests = {
                str(interest).strip().lower()
                for interest in candidate.get(
                    "interests",
                    [],
                )
                if str(interest).strip()
            }

            common_interests = (
                interests_set.intersection(
                    candidate_interests
                )
            )

            # ----------------------------------------------------------
            # Category
            # ----------------------------------------------------------
            candidate_category = str(
                candidate.get(
                    "category",
                    "",
                )
            ).strip()

            # ----------------------------------------------------------
            # Rating
            # ----------------------------------------------------------
            try:
                rating = float(
                    candidate.get(
                        "rating",
                        4.0,
                    )
                    or 4.0
                )
            except (
                TypeError,
                ValueError,
            ):
                rating = 4.0

            # ----------------------------------------------------------
            # Score
            # ----------------------------------------------------------
            score = 0.0

            # Same category.
            if (
                target_category
                and candidate_category.lower()
                == str(
                    target_category
                ).lower()
            ):
                score += 3.5

            # Interest overlap.
            score += (
                len(common_interests)
                * 2.0
            )

            # Distance.
            if distance_km is not None:
                score += max(
                    0.0,
                    5.0 - distance_km,
                )

            # Rating.
            score += rating * 0.5

            # Opening hours.
            if hours_compatible:
                score += 2.0
            else:
                score -= 3.0

            # Duration.
            if duration_difference <= 30:
                score += 1.5
            elif duration_difference <= 60:
                score += 0.5
            else:
                score -= 0.5

            # ----------------------------------------------------------
            # Transit estimate.
            # ----------------------------------------------------------
            transit_minutes = None

            if distance_km is not None:
                if distance_km <= 1.2:
                    transit_minutes = max(
                        5,
                        round(
                            (
                                distance_km
                                / 4.5
                            )
                            * 60
                        ),
                    )
                else:
                    transit_minutes = max(
                        12,
                        round(
                            (
                                distance_km
                                / 22.0
                            )
                            * 60
                        )
                        + 8,
                    )

            # ----------------------------------------------------------
            # Recommendation reason.
            # ----------------------------------------------------------
            reason_parts = []

            if candidate_category:
                reason_parts.append(
                    f"{candidate_category} alternative"
                )

            if distance_km is not None:
                reason_parts.append(
                    f"{round(distance_km, 1)} km "
                    f"from the original"
                )

            if common_interests:
                reason_parts.append(
                    "matches interests: "
                    + ", ".join(
                        list(
                            common_interests
                        )[:2]
                    )
                )

            if hours_compatible:
                reason_parts.append(
                    "available during the affected time"
                )

            if not reason_parts:
                reason_parts.append(
                    f"located in {destination}"
                )

            recommendation_reason = (
                "Recommended because "
                + ", ".join(
                    reason_parts
                )
                + "."
            )

            candidates_scored.append(
                {
                    "id": activity_id,
                    "activity_id": activity_id,
                    "name": candidate.get(
                        "name",
                        "Alternative Activity",
                    ),
                    "title": candidate.get(
                        "name",
                        "Alternative Activity",
                    ),
                    "category": candidate_category,
                    "destination": destination,
                    "distance_from_original_km": (
                        round(
                            distance_km,
                            2,
                        )
                        if distance_km is not None
                        else None
                    ),
                    "estimated_transit_minutes": (
                        transit_minutes
                    ),
                    "estimated_cost": cost,
                    "duration_minutes": (
                        candidate_duration
                    ),
                    "opening_time": candidate.get(
                        "opening_time"
                    ),
                    "closing_time": candidate.get(
                        "closing_time"
                    ),
                    "rating": rating,
                    "address": candidate.get(
                        "address"
                    ),
                    "latitude": candidate.get(
                        "latitude"
                    ),
                    "longitude": candidate.get(
                        "longitude"
                    ),
                    "interests": candidate.get(
                        "interests",
                        [],
                    ),
                    "hours_compatible": (
                        hours_compatible
                    ),
                    "currency_code": candidate.get(
                        "currency_code"
                    ),
                    "currency_symbol": candidate.get(
                        "currency_symbol"
                    ),
                    "similarity_score": round(
                        score,
                        2,
                    ),
                    "recommendation_reason": (
                        recommendation_reason
                    ),
                }
            )

        # --------------------------------------------------------------
        # Rank candidates.
        # --------------------------------------------------------------
        candidates_scored.sort(
            key=lambda candidate: candidate[
                "similarity_score"
            ],
            reverse=True,
        )

        top_candidates = candidates_scored[
            :limit
        ]

        recommended = (
            top_candidates[0]
            if top_candidates
            else None
        )

        return (
            top_candidates,
            recommended,
        )

    def generate_candidate_alternatives(
        self,
        target_item: Dict[str, Any],
        trip_interests: List[str],
        used_activity_ids: List[str],
        destination: str,
        max_cost: Optional[float] = None,
        limit: int = 4,
    ) -> Tuple[
        List[Dict[str, Any]],
        Optional[Dict[str, Any]],
    ]:
        """
        Synchronous wrapper around the destination-aware async
        Geoapify activity search.
        """

        return self._run_async(
            self._generate_candidate_alternatives_async(
                target_item=target_item,
                trip_interests=trip_interests,
                used_activity_ids=used_activity_ids,
                destination=destination,
                max_cost=max_cost,
                limit=limit,
            )
        )

    # ------------------------------------------------------------------
    # Step 7, 8, 9:
    # Rebuild Affected Portion, Validate & Optimize
    # ------------------------------------------------------------------
    def rebuild_and_optimize_itinerary(
        self,
        days: List[Dict[str, Any]],
        affected_items: List[Dict[str, Any]],
        recommended_alt: Optional[Dict[str, Any]],
        disruption_type: str,
        delay_minutes: int = 0,
        total_budget: float = 100000.0,
        travelers: int = 1,
        trip_interests: Optional[List[str]] = None,
        currency: str = "INR",
    ) -> Tuple[
        List[Dict[str, Any]],
        List[str],
    ]:
        """
        Reconstructs the affected itinerary portion.

        - Replaces cancelled activity.
        - Shifts delayed activity.
        - Handles budget reduction.
        - Handles interest changes.
        - Preserves bookings.
        - Re-optimizes modified days.
        """

        changes_applied = []

        updated_days = copy.deepcopy(
            days
        )

        affected_item_ids = {
            activity.get("id")
            for activity in affected_items
        }

        affected_activity_ids = {
            activity.get("activity_id")
            for activity in affected_items
            if activity.get("activity_id")
        }

        for day in updated_days:

            day_number = day.get(
                "day_number",
                1,
            )

            new_activities = []
            day_modified = False

            for activity in day.get(
                "activities",
                [],
            ):

                activity_record_id = (
                    activity.get("id")
                )

                activity_id = (
                    activity.get("activity_id")
                )

                is_affected = (
                    activity_record_id
                    in affected_item_ids
                    or (
                        activity_id
                        and activity_id
                        in affected_activity_ids
                    )
                )

                if not is_affected:
                    new_activities.append(
                        activity
                    )
                    continue

                # Never modify confirmed bookings.
                if activity.get(
                    "is_booking"
                ):
                    new_activities.append(
                        activity
                    )
                    continue

                day_modified = True

                old_name = (
                    activity.get(
                        "activity_name"
                    )
                    or activity.get(
                        "title"
                    )
                    or "Activity"
                )

                # ------------------------------------------------------
                # Cancellation
                # ------------------------------------------------------
                if disruption_type in (
                    "activity_cancelled",
                    "cancellation",
                    "activity_unavailable",
                ):

                    if recommended_alt:

                        alternative_cost = float(
                            recommended_alt.get(
                                "estimated_cost",
                                0.0,
                            )
                            or 0.0
                        )

                        alternative_currency = (
                            recommended_alt.get(
                                "currency_code"
                            )
                            or currency
                        )

                        changes_applied.append(
                            (
                                f"Day {day_number}: "
                                f"Replaced cancelled "
                                f"'{old_name}' with "
                                f"'{recommended_alt['name']}' "
                                f"({alternative_cost:.2f} "
                                f"{alternative_currency})."
                            )
                        )

                        activity[
                            "activity_id"
                        ] = recommended_alt.get(
                            "activity_id"
                        )

                        activity[
                            "activity_name"
                        ] = recommended_alt.get(
                            "name",
                            "Alternative Activity",
                        )

                        activity[
                            "title"
                        ] = recommended_alt.get(
                            "name",
                            "Alternative Activity",
                        )

                        activity[
                            "category"
                        ] = recommended_alt.get(
                            "category",
                            "General",
                        )

                        activity[
                            "location"
                        ] = recommended_alt.get(
                            "address",
                            "",
                        )

                        activity[
                            "cost"
                        ] = alternative_cost

                        activity[
                            "estimated_cost"
                        ] = alternative_cost

                        activity[
                            "currency"
                        ] = alternative_currency

                        activity[
                            "duration"
                        ] = (
                            f"{recommended_alt.get('duration_minutes', 90)} mins"
                        )

                        activity[
                            "transportation"
                        ] = (
                            "Local Transit"
                        )

                        activity[
                            "status"
                        ] = "Rerouted"

                        activity[
                            "notes"
                        ] = (
                            f"AI replaced "
                            f"{old_name} due to "
                            f"unexpected disruption."
                        )

                        new_activities.append(
                            activity
                        )

                    else:
                        changes_applied.append(
                            (
                                f"Day {day_number}: "
                                f"Removed cancelled "
                                f"activity '{old_name}' "
                                f"because no valid "
                                f"destination-local "
                                f"alternative was found."
                            )
                        )

                # ------------------------------------------------------
                # Transportation delay
                # ------------------------------------------------------
                elif disruption_type in (
                    "transportation_delayed",
                    "delay",
                ):

                    old_start = activity.get(
                        "start_time",
                        "09:00",
                    )

                    shifted_start = _minutes_to_time(
                        _time_to_minutes(
                            old_start
                        )
                        + delay_minutes
                    )

                    activity[
                        "start_time"
                    ] = shifted_start

                    activity[
                        "status"
                    ] = "Delayed"

                    changes_applied.append(
                        (
                            f"Day {day_number}: "
                            f"Shifted '{old_name}' "
                            f"by +{delay_minutes} "
                            f"minutes."
                        )
                    )

                    new_activities.append(
                        activity
                    )

                # ------------------------------------------------------
                # Budget reduction
                # ------------------------------------------------------
                elif disruption_type in (
                    "budget_reduced",
                    "budget",
                ):

                    current_cost = float(
                        activity.get(
                            "cost",
                            activity.get(
                                "estimated_cost",
                                0.0,
                            ),
                        )
                        or 0.0
                    )

                    alternative_cost = float(
                        recommended_alt.get(
                            "estimated_cost",
                            0.0,
                        )
                        if recommended_alt
                        else 0.0
                    )

                    if (
                        recommended_alt
                        and alternative_cost
                        < current_cost
                    ):

                        alternative_currency = (
                            recommended_alt.get(
                                "currency_code"
                            )
                            or currency
                        )

                        changes_applied.append(
                            (
                                f"Day {day_number}: "
                                f"Replaced costly "
                                f"'{old_name}' "
                                f"({current_cost:.2f} "
                                f"{currency}) with "
                                f"'{recommended_alt['name']}' "
                                f"({alternative_cost:.2f} "
                                f"{alternative_currency}) "
                                f"to reduce spending."
                            )
                        )

                        activity[
                            "activity_id"
                        ] = recommended_alt.get(
                            "activity_id"
                        )

                        activity[
                            "activity_name"
                        ] = recommended_alt.get(
                            "name",
                            "Alternative Activity",
                        )

                        activity[
                            "title"
                        ] = recommended_alt.get(
                            "name",
                            "Alternative Activity",
                        )

                        activity[
                            "category"
                        ] = recommended_alt.get(
                            "category",
                            "General",
                        )

                        activity[
                            "location"
                        ] = recommended_alt.get(
                            "address",
                            "",
                        )

                        activity[
                            "cost"
                        ] = alternative_cost

                        activity[
                            "estimated_cost"
                        ] = alternative_cost

                        activity[
                            "currency"
                        ] = alternative_currency

                        activity[
                            "duration"
                        ] = (
                            f"{recommended_alt.get('duration_minutes', 90)} mins"
                        )

                        activity[
                            "status"
                        ] = "Economized"

                        activity[
                            "notes"
                        ] = (
                            "Replaced with an "
                            "economical destination-local "
                            "alternative."
                        )

                    new_activities.append(
                        activity
                    )

                # ------------------------------------------------------
                # Interest change
                # ------------------------------------------------------
                elif disruption_type in (
                    "user_interests_changed",
                    "interests_changed",
                ):

                    if recommended_alt:

                        alternative_cost = float(
                            recommended_alt.get(
                                "estimated_cost",
                                0.0,
                            )
                            or 0.0
                        )

                        alternative_currency = (
                            recommended_alt.get(
                                "currency_code"
                            )
                            or currency
                        )

                        changes_applied.append(
                            (
                                f"Day {day_number}: "
                                f"Swapped '{old_name}' "
                                f"for "
                                f"'{recommended_alt['name']}' "
                                f"to match updated "
                                f"interests "
                                f"({', '.join(trip_interests or [])})."
                            )
                        )

                        activity[
                            "activity_id"
                        ] = recommended_alt.get(
                            "activity_id"
                        )

                        activity[
                            "activity_name"
                        ] = recommended_alt.get(
                            "name",
                            "Alternative Activity",
                        )

                        activity[
                            "title"
                        ] = recommended_alt.get(
                            "name",
                            "Alternative Activity",
                        )

                        activity[
                            "category"
                        ] = recommended_alt.get(
                            "category",
                            "General",
                        )

                        activity[
                            "location"
                        ] = recommended_alt.get(
                            "address",
                            "",
                        )

                        activity[
                            "cost"
                        ] = alternative_cost

                        activity[
                            "estimated_cost"
                        ] = alternative_cost

                        activity[
                            "currency"
                        ] = alternative_currency

                        activity[
                            "duration"
                        ] = (
                            f"{recommended_alt.get('duration_minutes', 90)} mins"
                        )

                        activity[
                            "status"
                        ] = "Adjusted"

                        activity[
                            "notes"
                        ] = (
                            "Realigned with "
                            "updated interests."
                        )

                    new_activities.append(
                        activity
                    )

                # ------------------------------------------------------
                # Hotel unavailable
                # ------------------------------------------------------
                elif disruption_type in (
                    "hotel_unavailable",
                    "hotel",
                ):

                    changes_applied.append(
                        (
                            f"Day {day_number}: "
                            f"Realigned the daily "
                            f"schedule after "
                            f"accommodation disruption."
                        )
                    )

                    activity[
                        "status"
                    ] = "Realigned"

                    new_activities.append(
                        activity
                    )

                else:
                    new_activities.append(
                        activity
                    )

            if day_modified:

                optimizer = ItineraryOptimizer(
                    total_budget=total_budget,
                    travelers=travelers,
                    interests=trip_interests,
                )

                optimized_activities = (
                    optimizer._reschedule_day_times(
                        day_number,
                        new_activities,
                        changes_applied,
                    )
                )

                day[
                    "activities"
                ] = optimized_activities

        return (
            updated_days,
            changes_applied,
        )

    # ------------------------------------------------------------------
    # Main Public Entrypoint:
    # Simulation Mode
    # ------------------------------------------------------------------
    def simulate_disruption(
        self,
        trip_id: str,
        disruption_type: str,
        activity_id: Optional[str] = None,
        title: Optional[str] = None,
        time: Optional[str] = None,
        delay_minutes: int = 0,
        cost_delta: float = 0.0,
        new_budget: Optional[float] = None,
        new_interests: Optional[List[str]] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Executes disruption simulation.

        Does NOT modify the SQLite database.
        """

        active_db = (
            db
            if db is not None
            else self._get_db()
        )

        try:

            # ----------------------------------------------------------
            # Step 1: Current state
            # ----------------------------------------------------------
            state = self.get_trip_state(
                trip_id,
                active_db,
            )

            days = state["days"]

            trip = state["trip"]

            destination = (
                state["destination"]
            )

            total_budget = (
                new_budget
                if new_budget is not None
                else (
                    state["budget"]
                    - cost_delta
                )
            )

            travelers = (
                state["travelers"]
            )

            trip_interests = (
                new_interests
                if new_interests is not None
                else state["interests"]
            )

            currency = (
                state["currency"]
                or "INR"
            )

            # ----------------------------------------------------------
            # Step 2: Affected items
            # ----------------------------------------------------------
            affected_items = (
                self.identify_affected_items(
                    days=days,
                    disruption_type=disruption_type,
                    activity_id=activity_id,
                    title=title,
                    time=time,
                    new_interests=trip_interests,
                )
            )

            # ----------------------------------------------------------
            # Step 3: Downstream impacts
            # ----------------------------------------------------------
            downstream_impacts = (
                self.identify_downstream_impacts(
                    days=days,
                    affected_items=affected_items,
                    disruption_type=disruption_type,
                    delay_minutes=delay_minutes,
                )
            )

            # ----------------------------------------------------------
            # Step 4, 5, 6:
            # Destination-aware alternatives
            # ----------------------------------------------------------
            used_ids = [
                activity.get(
                    "activity_id"
                )
                for day in days
                for activity in day.get(
                    "activities",
                    [],
                )
                if activity.get(
                    "activity_id"
                )
            ]

            alternatives = []
            recommended_alt = None

            if affected_items:

                target_item = (
                    affected_items[0]
                )

                alternatives, recommended_alt = (
                    self.generate_candidate_alternatives(
                        target_item=target_item,
                        trip_interests=trip_interests,
                        used_activity_ids=used_ids,
                        destination=destination,
                    )
                )

            # ----------------------------------------------------------
            # Step 7, 8, 9:
            # Rebuild + optimize
            # ----------------------------------------------------------
            updated_days, changes_made = (
                self.rebuild_and_optimize_itinerary(
                    days=days,
                    affected_items=affected_items,
                    recommended_alt=recommended_alt,
                    disruption_type=disruption_type,
                    delay_minutes=delay_minutes,
                    total_budget=total_budget,
                    travelers=travelers,
                    trip_interests=trip_interests,
                    currency=currency,
                )
            )

            # ----------------------------------------------------------
            # Step 8: Constraint audit
            # ----------------------------------------------------------
            constraint_report = (
                audit_itinerary_constraints(
                    days=updated_days,
                    total_budget=total_budget,
                    travelers=travelers,
                )
            )

            # ----------------------------------------------------------
            # Cost impact
            # ----------------------------------------------------------
            old_spending = calculate_total_cost(
                days,
                travelers=travelers,
            )

            new_spending = calculate_total_cost(
                updated_days,
                travelers=travelers,
            )

            spending_delta = round(
                new_spending - old_spending,
                2,
            )

            new_remaining_budget = max(
                0.0,
                total_budget - new_spending,
            )

            # ----------------------------------------------------------
            # Travel distance impact
            # ----------------------------------------------------------
            optimizer = ItineraryOptimizer(
                total_budget=total_budget,
                travelers=travelers,
            )

            old_distance = sum(
                optimizer._calculate_route_distance(
                    day.get(
                        "activities",
                        [],
                    )
                )
                for day in days
            )

            new_distance = sum(
                optimizer._calculate_route_distance(
                    day.get(
                        "activities",
                        [],
                    )
                )
                for day in updated_days
            )

            distance_delta = round(
                new_distance - old_distance,
                2,
            )

            # ----------------------------------------------------------
            # Reason
            # ----------------------------------------------------------
            target_description = (
                affected_items[0].get(
                    "activity_name",
                    "target activity",
                )
                if affected_items
                else "Trip Schedule"
            )

            reason_string = (
                f"{disruption_type.replace('_', ' ').title()} "
                f"({target_description})"
            )

            return {
                "simulation_mode": True,
                "trip_id": trip_id,
                "destination": destination,
                "disruption_type": disruption_type,
                "delay_minutes": delay_minutes,
                "cost_delta": cost_delta,
                "new_budget": new_budget,
                "new_interests": new_interests,
                "reason_for_disruption": reason_string,
                "original_itinerary": days,
                "affected_items": affected_items,
                "downstream_impacts": downstream_impacts,
                "alternatives": alternatives,
                "recommended_alternative": recommended_alt,
                "updated_itinerary": updated_days,
                "budget_impact": {
                    "original_budget": state["budget"],
                    "revised_budget": total_budget,
                    "original_spending": old_spending,
                    "updated_spending": new_spending,
                    "spending_delta": spending_delta,
                    "new_remaining_budget": round(
                        new_remaining_budget,
                        2,
                    ),
                    "currency": currency,
                },
                "travel_impact": {
                    "original_distance_km": round(
                        old_distance,
                        2,
                    ),
                    "updated_distance_km": round(
                        new_distance,
                        2,
                    ),
                    "distance_delta_km": distance_delta,
                },
                "changes_made": changes_made,
                "constraint_status": {
                    "is_valid": constraint_report[
                        "is_valid"
                    ],
                    "total_conflicts": constraint_report[
                        "total_conflicts"
                    ],
                },
            }

        finally:

            if (
                self._external_db is None
                and active_db
            ):
                active_db.close()

    # ------------------------------------------------------------------
    # Main Public Entrypoint:
    # Apply Replan
    # ------------------------------------------------------------------
    def replan_and_apply(
        self,
        trip_id: str,
        disruption_type: str = "activity_cancelled",
        activity_id: Optional[str] = None,
        title: Optional[str] = None,
        time: Optional[str] = None,
        delay_minutes: int = 0,
        cost_delta: float = 0.0,
        new_budget: Optional[float] = None,
        new_interests: Optional[List[str]] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Executes replanning and commits changes to SQLite.
        """

        active_db = (
            db
            if db is not None
            else self._get_db()
        )

        try:

            # ----------------------------------------------------------
            # 1. Simulate first
            # ----------------------------------------------------------
            simulation_result = (
                self.simulate_disruption(
                    trip_id=trip_id,
                    disruption_type=disruption_type,
                    activity_id=activity_id,
                    title=title,
                    time=time,
                    delay_minutes=delay_minutes,
                    cost_delta=cost_delta,
                    new_budget=new_budget,
                    new_interests=new_interests,
                    db=active_db,
                )
            )

            updated_days = (
                simulation_result[
                    "updated_itinerary"
                ]
            )

            new_spending = (
                simulation_result[
                    "budget_impact"
                ][
                    "updated_spending"
                ]
            )

            currency = (
                simulation_result[
                    "budget_impact"
                ].get(
                    "currency",
                    "INR",
                )
            )

            # ----------------------------------------------------------
            # 2. Remove existing itinerary items
            # ----------------------------------------------------------
            (
                active_db.query(
                    ItineraryItemModel
                )
                .filter(
                    ItineraryItemModel.trip_id
                    == trip_id
                )
                .delete()
            )

            # ----------------------------------------------------------
            # 3. Save rebuilt itinerary
            # ----------------------------------------------------------
            for day in updated_days:

                day_number = day.get(
                    "day_number",
                    1,
                )

                for order_index, activity in enumerate(
                    day.get(
                        "activities",
                        [],
                    )
                ):

                    if activity.get(
                        "is_booking"
                    ):
                        continue

                    item_id = (
                        activity.get("id")
                        or f"item-{uuid.uuid4().hex[:8]}"
                    )

                    # Database itinerary items should not use
                    # external activity IDs as primary IDs.
                    if item_id.startswith(
                        "act-"
                    ):
                        item_id = (
                            f"item-{uuid.uuid4().hex[:8]}"
                        )

                    activity_currency = (
                        activity.get(
                            "currency"
                        )
                        or currency
                    )

                    new_item = (
                        ItineraryItemModel(
                            id=item_id,
                            trip_id=trip_id,
                            day_number=day_number,
                            date=day.get(
                                "date",
                                "2026-10-10",
                            ),
                            time=activity.get(
                                "start_time",
                                "09:30",
                            ),
                            title=(
                                activity.get(
                                    "activity_name"
                                )
                                or activity.get(
                                    "title",
                                    "Activity",
                                )
                            ),
                            category=activity.get(
                                "category",
                                "General",
                            ),
                            duration=activity.get(
                                "duration",
                                "90 mins",
                            ),
                            location=activity.get(
                                "location",
                                "",
                            ),
                            cost=float(
                                activity.get(
                                    "cost",
                                    activity.get(
                                        "estimated_cost",
                                        0.0,
                                    ),
                                )
                                or 0.0
                            ),
                            currency=activity_currency,
                            transportation=activity.get(
                                "transportation",
                                "Metro",
                            ),
                            status=activity.get(
                                "status",
                                "Confirmed",
                            ),
                            notes=activity.get(
                                "notes",
                                "Replanned by AI Co-pilot",
                            ),
                            order=order_index + 1,
                        )
                    )

                    active_db.add(
                        new_item
                    )

            # ----------------------------------------------------------
            # 4. Update trip
            # ----------------------------------------------------------
            trip = (
                active_db.query(
                    TripModel
                )
                .filter(
                    TripModel.id == trip_id
                )
                .first()
            )

            if trip:

                trip.spending = (
                    new_spending
                )

                if new_budget is not None:
                    trip.budget = (
                        new_budget
                    )

                if new_interests is not None:
                    trip.interests = json.dumps(
                        new_interests
                    )

            # ----------------------------------------------------------
            # 5. Update budget record
            # ----------------------------------------------------------
            budget_record = (
                active_db.query(
                    BudgetModel
                )
                .filter(
                    BudgetModel.trip_id
                    == trip_id
                )
                .first()
            )

            if budget_record:

                budget_record.estimated_spending = (
                    new_spending
                )

                budget_record.activities = (
                    new_spending
                )

                if new_budget is not None:
                    budget_record.total_budget = (
                        new_budget
                    )

                budget_record.currency = (
                    currency
                )

            # ----------------------------------------------------------
            # 6. Record disruption
            # ----------------------------------------------------------
            recommended = (
                simulation_result.get(
                    "recommended_alternative"
                )
            )

            recommendation_reason = (
                recommended.get(
                    "recommendation_reason"
                )
                if recommended
                else "Schedule optimized"
            )

            changes = (
                simulation_result.get(
                    "changes_made",
                    [],
                )
            )

            disruption_record = (
                DisruptionModel(
                    id=(
                        f"disrupt-"
                        f"{uuid.uuid4().hex[:8]}"
                    ),
                    trip_id=trip_id,
                    disruption_type=disruption_type,
                    title=simulation_result[
                        "reason_for_disruption"
                    ],
                    severity="warning",
                    description=(
                        "Resolved via automatic "
                        "replanning: "
                        + (
                            "; ".join(
                                changes[:2]
                            )
                            if changes
                            else "Schedule optimized"
                        )
                    ),
                    ai_resolution=(
                        recommendation_reason
                    ),
                    timestamp=(
                        datetime.datetime.now()
                        .strftime(
                            "%Y-%m-%d %H:%M"
                        )
                    ),
                    resolved=True,
                )
            )

            active_db.add(
                disruption_record
            )

            # ----------------------------------------------------------
            # 7. Commit
            # ----------------------------------------------------------
            active_db.commit()

            # ----------------------------------------------------------
            # 8. Retrieve saved itinerary
            # ----------------------------------------------------------
            final_saved_items = (
                active_db.query(
                    ItineraryItemModel
                )
                .filter(
                    ItineraryItemModel.trip_id
                    == trip_id
                )
                .order_by(
                    ItineraryItemModel.day_number,
                    ItineraryItemModel.order,
                )
                .all()
            )

            return {
                "success": True,
                "simulation_mode": False,
                "trip_id": trip_id,
                "status": "replan_applied",
                "disruptions_addressed": 1,
                "reason_for_disruption": (
                    simulation_result[
                        "reason_for_disruption"
                    ]
                ),
                "affected_items": (
                    simulation_result[
                        "affected_items"
                    ]
                ),
                "recommended_alternative": (
                    recommended
                ),
                "summary_of_changes": (
                    "; ".join(changes)
                    if changes
                    else "Schedule adjusted"
                ),
                "affected_itinerary_count": len(
                    simulation_result[
                        "affected_items"
                    ]
                ),
                "updated_spending": new_spending,
                "budget_impact": (
                    simulation_result[
                        "budget_impact"
                    ]
                ),
                "travel_impact": (
                    simulation_result[
                        "travel_impact"
                    ]
                ),
                "changes_made": changes,
                "updated_itinerary": (
                    final_saved_items
                ),
            }

        finally:

            if (
                self._external_db is None
                and active_db
            ):
                active_db.close()


# Default manager instance.
default_disruption_manager = DisruptionManager()