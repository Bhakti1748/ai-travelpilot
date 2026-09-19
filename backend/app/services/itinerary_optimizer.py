"""
TravelPilot Itinerary Optimizer

Deterministic optimization engine that:
- Groups geographically close activities to minimize intra-day travel
- Estimates realistic travel time and transportation mode
- Respects venue opening and closing hours
- Preserves full activity durations
- Respects traveler interests and total budget
- Preserves confirmed bookings and fixed reservations
- Eliminates duplicate activities
- Improves activity/category diversity
- Eliminates schedule overlaps and travel deficits
- Provides optimization metrics
"""

import itertools
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.constraint_engine import (
    _minutes_to_time,
    _parse_duration_minutes,
    _time_to_minutes,
    calculate_total_cost,
)
from app.services.dataset_service import (
    dataset_service,
    haversine_distance_km,
)

logger = logging.getLogger(__name__)


class ItineraryOptimizer:
    """
    Deterministic itinerary optimizer for TravelPilot.
    """

    def __init__(
        self,
        total_budget: float,
        travelers: int = 1,
        interests: Optional[List[str]] = None,
        candidates_map: Optional[Dict[str, Dict[str, Any]]] = None,
        min_buffer_mins: int = 15,
        default_day_start: str = "09:30",
    ):
        self.total_budget = total_budget
        self.travelers = max(1, travelers)

        self.interests = [
            str(i).strip().lower()
            for i in (interests or [])
        ]

        self.min_buffer_mins = min_buffer_mins
        self.default_day_start = default_day_start

        # Prepare candidate dictionary.
        if candidates_map:
            self.candidates_map = candidates_map
        else:
            all_acts = dataset_service.all_activities

            self.candidates_map = {
                a["id"]: a
                for a in all_acts
            }

    # =========================================================
    # VENUE HELPERS
    # =========================================================

    def _get_venue(
        self,
        act: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve full venue metadata for an activity.
        """

        act_id = (
            act.get("activity_id")
            or act.get("id")
        )

        if act_id and act_id in self.candidates_map:
            return self.candidates_map[act_id]

        if act_id:
            return dataset_service.get_activity(
                act_id
            )

        return None

    def _get_activity_category(
        self,
        activity: Dict[str, Any],
    ) -> str:
        """
        Return the normalized activity category.
        """

        category = activity.get("category")

        if category:
            return str(category).strip()

        venue = self._get_venue(activity)

        if venue:
            category = venue.get("category")

            if category:
                return str(category).strip()

        return "Other"

    def _get_activity_interests(
        self,
        activity: Dict[str, Any],
    ) -> Set[str]:
        """
        Return normalized interests associated with an activity.
        """

        interests = activity.get("interests")

        if not interests:
            venue = self._get_venue(activity)

            if venue:
                interests = venue.get(
                    "interests",
                    [],
                )

        return {
            str(i).strip().lower()
            for i in (interests or [])
        }

    def _is_confirmed_booking(
        self,
        act: Dict[str, Any],
    ) -> bool:
        """
        Determine whether an activity is a
        locked/confirmed booking.
        """

        if act.get("is_booking") is True:
            return True

        if act.get("locked") is True:
            return True

        if act.get("booking_type"):
            return True

        if act.get("reference_code"):
            return True

        if (
            act.get("status") == "Confirmed"
            and act.get("provider")
        ):
            return True

        return False

    # =========================================================
    # TRANSPORTATION
    # =========================================================

    def _compute_transit_time(
        self,
        dist_km: float,
    ) -> int:
        """
        Estimate travel time between two activities.

        These are planning estimates only.
        They do not use live traffic or live
        public-transit data.
        """

        if dist_km <= 1.2:
            # Short distance: walking.
            walking_time = (
                dist_km / 4.5
            ) * 60

            return max(
                5,
                round(walking_time + 2),
            )

        if dist_km <= 5.0:
            # Medium city distance.
            transit_time = (
                dist_km / 22.0
            ) * 60

            return max(
                12,
                round(transit_time + 8),
            )

        if dist_km <= 15.0:
            # Longer city distance.
            transit_time = (
                dist_km / 25.0
            ) * 60

            return max(
                20,
                round(transit_time + 12),
            )

        # Long-distance movement.
        transit_time = (
            dist_km / 35.0
        ) * 60

        return max(
            30,
            round(transit_time + 15),
        )

    def _get_transport_mode(
        self,
        dist_km: float,
    ) -> str:
        """
        Select an approximate transportation mode
        based on distance.

        This is a planning heuristic and does not
        use live traffic or transit availability.
        """

        if dist_km <= 1.2:
            return "Walking"

        if dist_km <= 5.0:
            return "Metro"

        if dist_km <= 15.0:
            return "Metro / Local Transit"

        return "Taxi / Long-distance Transit"

    # =========================================================
    # ROUTE CALCULATIONS
    # =========================================================

    def _calculate_route_distance(
        self,
        activities: List[Dict[str, Any]],
    ) -> float:
        """
        Calculate total sequential distance in km.
        """

        total_dist = 0.0

        for i in range(
            len(activities) - 1
        ):
            v1 = self._get_venue(
                activities[i]
            )

            v2 = self._get_venue(
                activities[i + 1]
            )

            if v1 and v2:

                lat1 = v1.get("latitude")
                lon1 = v1.get("longitude")

                lat2 = v2.get("latitude")
                lon2 = v2.get("longitude")

                if None not in (
                    lat1,
                    lon1,
                    lat2,
                    lon2,
                ):
                    total_dist += (
                        haversine_distance_km(
                            lat1,
                            lon1,
                            lat2,
                            lon2,
                        )
                    )

        return round(
            total_dist,
            3,
        )

    def _calculate_route_transit_mins(
        self,
        activities: List[Dict[str, Any]],
    ) -> int:
        """
        Calculate total estimated transit time.
        """

        total_mins = 0

        for i in range(
            len(activities) - 1
        ):
            v1 = self._get_venue(
                activities[i]
            )

            v2 = self._get_venue(
                activities[i + 1]
            )

            if v1 and v2:

                lat1 = v1.get("latitude")
                lon1 = v1.get("longitude")

                lat2 = v2.get("latitude")
                lon2 = v2.get("longitude")

                if None not in (
                    lat1,
                    lon1,
                    lat2,
                    lon2,
                ):

                    distance = (
                        haversine_distance_km(
                            lat1,
                            lon1,
                            lat2,
                            lon2,
                        )
                    )

                    total_mins += (
                        self._compute_transit_time(
                            distance
                        )
                    )

                else:
                    total_mins += (
                        self.min_buffer_mins
                    )

            else:
                total_mins += (
                    self.min_buffer_mins
                )

        return total_mins

    # =========================================================
    # CANDIDATE SCORING
    # =========================================================

    def _score_replacement_candidate(
        self,
        candidate: Dict[str, Any],
        day_activities: List[Dict[str, Any]],
        old_activity: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Score a candidate replacement.

        Higher score = better replacement.

        Factors:
        - User interest match
        - Category diversity
        - Lower travel burden
        - Lower cost when useful
        """

        score = 0.0

        candidate_category = str(
            candidate.get(
                "category",
                "Other",
            )
        ).strip().lower()

        candidate_interests = {
            str(i).strip().lower()
            for i in candidate.get(
                "interests",
                [],
            )
        }

        # -----------------------------------------------------
        # 1. USER INTEREST MATCH
        # -----------------------------------------------------

        matching_interests = (
            candidate_interests
            .intersection(
                self.interests
            )
        )

        score += (
            len(matching_interests)
            * 20
        )

        # Direct category-interest match.
        if candidate_category in self.interests:
            score += 15

        # -----------------------------------------------------
        # 2. CATEGORY DIVERSITY
        # -----------------------------------------------------

        existing_categories = [
            self._get_activity_category(
                activity
            ).strip().lower()
            for activity in day_activities
        ]

        category_count = (
            existing_categories.count(
                candidate_category
            )
        )

        if category_count == 0:
            score += 25

        elif category_count == 1:
            score += 10

        else:
            # Avoid excessive repetition.
            score -= (
                category_count * 15
            )

        # -----------------------------------------------------
        # 3. COST
        # -----------------------------------------------------

        candidate_cost = float(
            candidate.get(
                "estimated_cost",
                0.0,
            )
            or 0.0
        )

        if candidate_cost == 0:
            score += 5

        elif candidate_cost < 1000:
            score += 3

        # -----------------------------------------------------
        # 4. LOCATION
        # -----------------------------------------------------

        if old_activity:

            old_venue = self._get_venue(
                old_activity
            )

            if old_venue:

                old_lat = old_venue.get(
                    "latitude"
                )
                old_lon = old_venue.get(
                    "longitude"
                )

                candidate_lat = candidate.get(
                    "latitude"
                )
                candidate_lon = candidate.get(
                    "longitude"
                )

                if None not in (
                    old_lat,
                    old_lon,
                    candidate_lat,
                    candidate_lon,
                ):
                    distance = (
                        haversine_distance_km(
                            old_lat,
                            old_lon,
                            candidate_lat,
                            candidate_lon,
                        )
                    )

                    # Prefer nearby alternatives.
                    score -= min(
                        distance * 2,
                        30,
                    )

        return score

    def _find_best_replacement(
        self,
        activity: Dict[str, Any],
        day_activities: List[Dict[str, Any]],
        used_ids: Set[str],
        budget_only: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best available replacement candidate.
        """

        candidates = []

        for candidate in self.candidates_map.values():

            candidate_id = candidate.get(
                "id"
            )

            if not candidate_id:
                continue

            if candidate_id in used_ids:
                continue

            candidate_cost = float(
                candidate.get(
                    "estimated_cost",
                    0.0,
                )
                or 0.0
            )

            old_cost = float(
                activity.get(
                    "estimated_cost",
                    activity.get(
                        "cost",
                        0.0,
                    ),
                )
                or 0.0
            )

            if budget_only:
                if candidate_cost >= old_cost:
                    continue

            score = (
                self._score_replacement_candidate(
                    candidate,
                    day_activities,
                    activity,
                )
            )

            candidates.append(
                (
                    score,
                    candidate,
                )
            )

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return candidates[0][1]

    # =========================================================
    # MAIN OPTIMIZER
    # =========================================================

    def optimize(
        self,
        days: List[Dict[str, Any]],
    ) -> Tuple[
        List[Dict[str, Any]],
        Dict[str, Any],
    ]:
        """
        Execute the full optimization process.
        """

        adjustments: List[str] = []

        initial_distance = sum(
            self._calculate_route_distance(
                d.get("activities", [])
            )
            for d in days
        )

        initial_transit_mins = sum(
            self._calculate_route_transit_mins(
                d.get("activities", [])
            )
            for d in days
        )

        # -------------------------------------------------
        # STEP 1: Remove duplicates
        # -------------------------------------------------

        days = self._deduplicate_activities(
            days,
            adjustments,
        )

        # -------------------------------------------------
        # STEP 2: Improve category diversity
        # -------------------------------------------------

        days = self._improve_category_diversity(
            days,
            adjustments,
        )

        # -------------------------------------------------
        # STEP 3: Budget optimization
        # -------------------------------------------------

        days = self._optimize_budget(
            days,
            adjustments,
        )

        # -------------------------------------------------
        # STEP 4: Geographic route optimization
        # -------------------------------------------------

        optimized_days = []

        for day in days:

            day_copy = dict(day)

            raw_activities = day.get(
                "activities",
                [],
            )

            if len(raw_activities) >= 2:

                optimized_activities = (
                    self._optimize_day_route(
                        day_copy.get(
                            "day_number",
                            1,
                        ),
                        raw_activities,
                        adjustments,
                    )
                )

                day_copy[
                    "activities"
                ] = optimized_activities

            else:

                day_copy[
                    "activities"
                ] = raw_activities

            optimized_days.append(
                day_copy
            )

        # -------------------------------------------------
        # STEP 5: Time scheduling
        # -------------------------------------------------

        for day in optimized_days:

            day["activities"] = (
                self._reschedule_day_times(
                    day.get(
                        "day_number",
                        1,
                    ),
                    day.get(
                        "activities",
                        [],
                    ),
                    adjustments,
                )
            )

        # -------------------------------------------------
        # FINAL METRICS
        # -------------------------------------------------

        final_distance = sum(
            self._calculate_route_distance(
                d.get("activities", [])
            )
            for d in optimized_days
        )

        final_transit_mins = sum(
            self._calculate_route_transit_mins(
                d.get("activities", [])
            )
            for d in optimized_days
        )

        distance_saved = round(
            max(
                0.0,
                initial_distance
                - final_distance,
            ),
            2,
        )

        time_saved = max(
            0,
            initial_transit_mins
            - final_transit_mins,
        )

        final_cost = calculate_total_cost(
            optimized_days,
            travelers=self.travelers,
        )

        metrics = {
            "initial_distance_km": round(
                initial_distance,
                2,
            ),
            "optimized_distance_km": round(
                final_distance,
                2,
            ),
            "distance_saved_km": distance_saved,
            "initial_transit_mins": (
                initial_transit_mins
            ),
            "optimized_transit_mins": (
                final_transit_mins
            ),
            "travel_time_saved_mins": (
                time_saved
            ),
            "total_budget": (
                self.total_budget
            ),
            "final_total_cost": final_cost,
            "budget_remaining": max(
                0,
                self.total_budget
                - final_cost,
            ),
            "budget_status": (
                "Within budget"
                if final_cost
                <= self.total_budget
                else "Over budget"
            ),
            "adjustments_count": len(
                adjustments
            ),
            "adjustments_applied": (
                adjustments
            ),
        }

        return (
            optimized_days,
            metrics,
        )

    # =========================================================
    # DUPLICATE REMOVAL
    # =========================================================

    def _deduplicate_activities(
        self,
        days: List[Dict[str, Any]],
        adjustments: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Replace duplicated activities with
        better unused candidate venues.
        """

        seen_ids: Set[str] = set()

        all_used_ids: Set[str] = set()

        for day in days:

            for activity in day.get(
                "activities",
                [],
            ):

                activity_id = (
                    activity.get(
                        "activity_id"
                    )
                    or activity.get("id")
                )

                if activity_id:
                    all_used_ids.add(
                        activity_id
                    )

        new_days = []

        for day in days:

            day_copy = dict(day)

            clean_activities = []

            current_day_activities = []

            for activity in day.get(
                "activities",
                [],
            ):

                activity_id = (
                    activity.get(
                        "activity_id"
                    )
                    or activity.get("id")
                )

                is_booking = (
                    self._is_confirmed_booking(
                        activity
                    )
                )

                # -------------------------------------------------
                # DUPLICATE
                # -------------------------------------------------

                if (
                    activity_id
                    and activity_id in seen_ids
                    and not is_booking
                ):

                    replacement = (
                        self._find_best_replacement(
                            activity,
                            current_day_activities,
                            all_used_ids,
                        )
                    )

                    if replacement:

                        old_name = (
                            activity.get(
                                "activity_name"
                            )
                            or activity.get(
                                "title",
                                activity_id,
                            )
                        )

                        adjustments.append(
                            f"Deduplication: Replaced "
                            f"duplicate '{old_name}' "
                            f"on Day "
                            f"{day.get('day_number', 1)} "
                            f"with "
                            f"'{replacement['name']}'."
                        )

                        activity_copy = (
                            self._build_replacement_activity(
                                activity,
                                replacement,
                            )
                        )

                        seen_ids.add(
                            replacement["id"]
                        )

                        all_used_ids.add(
                            replacement["id"]
                        )

                        clean_activities.append(
                            activity_copy
                        )

                        current_day_activities.append(
                            activity_copy
                        )

                        continue

                if activity_id:
                    seen_ids.add(
                        activity_id
                    )

                clean_activities.append(
                    activity
                )

                current_day_activities.append(
                    activity
                )

            day_copy[
                "activities"
            ] = clean_activities

            new_days.append(
                day_copy
            )

        return new_days

    # =========================================================
    # REPLACEMENT BUILDER
    # =========================================================

    def _build_replacement_activity(
        self,
        old_activity: Dict[str, Any],
        replacement: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build an itinerary activity from a
        replacement candidate.
        """

        activity_copy = dict(
            old_activity
        )

        activity_copy[
            "activity_id"
        ] = replacement.get(
            "id"
        )

        activity_copy[
            "activity_name"
        ] = replacement.get(
            "name",
            "Unnamed activity",
        )

        activity_copy[
            "title"
        ] = replacement.get(
            "name",
            "Unnamed activity",
        )

        activity_copy[
            "category"
        ] = replacement.get(
            "category",
            "Other",
        )

        activity_copy[
            "location"
        ] = replacement.get(
            "address",
            "",
        )

        activity_copy[
            "address"
        ] = replacement.get(
            "address",
            "",
        )

        activity_copy[
            "latitude"
        ] = replacement.get(
            "latitude"
        )

        activity_copy[
            "longitude"
        ] = replacement.get(
            "longitude"
        )

        activity_copy[
            "estimated_cost"
        ] = replacement.get(
            "estimated_cost",
            0.0,
        )

        duration = replacement.get(
            "duration_minutes",
            90,
        )

        activity_copy[
            "duration"
        ] = f"{duration} mins"

        activity_copy[
            "opening_time"
        ] = replacement.get(
            "opening_time"
        )

        activity_copy[
            "closing_time"
        ] = replacement.get(
            "closing_time"
        )

        activity_copy[
            "interests"
        ] = replacement.get(
            "interests",
            [],
        )

        return activity_copy

    # =========================================================
    # CATEGORY DIVERSITY
    # =========================================================

    def _improve_category_diversity(
        self,
        days: List[Dict[str, Any]],
        adjustments: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Reduce excessive repetition of the same
        activity category within a day.

        Example:

            Museum
            Museum
            Museum

        can become:

            Museum
            Park
            Historical Site

        when suitable unused candidates exist.

        Confirmed bookings are never replaced.
        """

        all_used_ids: Set[str] = set()

        for day in days:

            for activity in day.get(
                "activities",
                [],
            ):

                activity_id = (
                    activity.get(
                        "activity_id"
                    )
                    or activity.get("id")
                )

                if activity_id:
                    all_used_ids.add(
                        activity_id
                    )

        for day in days:

            activities = day.get(
                "activities",
                [],
            )

            if len(activities) < 3:
                continue

            category_counts: Dict[
                str,
                int,
            ] = {}

            for activity in activities:

                category = (
                    self._get_activity_category(
                        activity
                    )
                    .strip()
                    .lower()
                )

                category_counts[
                    category
                ] = (
                    category_counts.get(
                        category,
                        0,
                    )
                    + 1
                )

            for index, activity in enumerate(
                list(activities)
            ):

                if self._is_confirmed_booking(
                    activity
                ):
                    continue

                current_category = (
                    self._get_activity_category(
                        activity
                    )
                    .strip()
                    .lower()
                )

                # Allow up to two activities
                # from the same category.
                if (
                    category_counts.get(
                        current_category,
                        0,
                    )
                    <= 2
                ):
                    continue

                replacement = (
                    self._find_best_replacement(
                        activity,
                        activities,
                        all_used_ids,
                    )
                )

                if not replacement:
                    continue

                replacement_category = (
                    str(
                        replacement.get(
                            "category",
                            "Other",
                        )
                    )
                    .strip()
                    .lower()
                )

                # Do not replace with the
                # same category.
                if (
                    replacement_category
                    == current_category
                ):
                    continue

                old_name = (
                    activity.get(
                        "activity_name"
                    )
                    or activity.get(
                        "title",
                        "Activity",
                    )
                )

                new_activity = (
                    self._build_replacement_activity(
                        activity,
                        replacement,
                    )
                )

                activities[index] = (
                    new_activity
                )

                old_id = (
                    activity.get(
                        "activity_id"
                    )
                    or activity.get("id")
                )

                new_id = replacement.get(
                    "id"
                )

                if old_id:
                    all_used_ids.discard(
                        old_id
                    )

                if new_id:
                    all_used_ids.add(
                        new_id
                    )

                category_counts[
                    current_category
                ] -= 1

                category_counts[
                    replacement_category
                ] = (
                    category_counts.get(
                        replacement_category,
                        0,
                    )
                    + 1
                )

                adjustments.append(
                    f"Category diversity: "
                    f"Replaced '{old_name}' "
                    f"on Day "
                    f"{day.get('day_number', 1)} "
                    f"with "
                    f"'{replacement.get('name')}' "
                    f"to provide a more varied "
                    f"experience."
                )

        return days

    # =========================================================
    # BUDGET OPTIMIZATION
    # =========================================================

    def _optimize_budget(
        self,
        days: List[Dict[str, Any]],
        adjustments: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Swap costly flexible activities for
        cheaper alternatives if total exceeds
        the budget.
        """

        total_cost = calculate_total_cost(
            days,
            travelers=self.travelers,
        )

        if total_cost <= self.total_budget:
            return days

        adjustments.append(
            f"Budget constraint: Total cost "
            f"({total_cost:,.0f}) exceeds budget "
            f"({self.total_budget:,.0f}). "
            f"Rebalancing activities."
        )

        all_used_ids = {
            activity.get(
                "activity_id"
            )
            or activity.get("id")
            for day in days
            for activity in day.get(
                "activities",
                [],
            )
            if (
                activity.get(
                    "activity_id"
                )
                or activity.get("id")
            )
        }

        for day in days:

            if total_cost <= self.total_budget:
                break

            day_activities = day.get(
                "activities",
                [],
            )

            # Sort expensive flexible
            # activities first.
            sortable = sorted(
                enumerate(
                    day_activities
                ),
                key=lambda item: float(
                    item[1].get(
                        "estimated_cost",
                        item[1].get(
                            "cost",
                            0.0,
                        ),
                    )
                    or 0.0
                ),
                reverse=True,
            )

            for index, activity in sortable:

                if total_cost <= self.total_budget:
                    break

                if self._is_confirmed_booking(
                    activity
                ):
                    continue

                old_cost = float(
                    activity.get(
                        "estimated_cost",
                        activity.get(
                            "cost",
                            0.0,
                        ),
                    )
                    or 0.0
                )

                replacement = (
                    self._find_best_replacement(
                        activity,
                        day_activities,
                        all_used_ids,
                        budget_only=True,
                    )
                )

                if not replacement:
                    continue

                new_cost = float(
                    replacement.get(
                        "estimated_cost",
                        0.0,
                    )
                    or 0.0
                )

                if new_cost >= old_cost:
                    continue

                old_name = (
                    activity.get(
                        "activity_name"
                    )
                    or activity.get(
                        "title",
                        "Activity",
                    )
                )

                new_activity = (
                    self._build_replacement_activity(
                        activity,
                        replacement,
                    )
                )

                saved = (
                    old_cost
                    - new_cost
                ) * self.travelers

                new_activity[
                    "reason"
                ] = (
                    f"Budget optimized "
                    f"(estimated saving "
                    f"{saved:,.0f})."
                )

                day_activities[
                    index
                ] = new_activity

                old_id = (
                    activity.get(
                        "activity_id"
                    )
                    or activity.get("id")
                )

                new_id = replacement.get(
                    "id"
                )

                if old_id:
                    all_used_ids.discard(
                        old_id
                    )

                if new_id:
                    all_used_ids.add(
                        new_id
                    )

                total_cost -= saved

                adjustments.append(
                    f"Budget swap: Replaced "
                    f"'{old_name}' with "
                    f"'{replacement.get('name')}' "
                    f"on Day "
                    f"{day.get('day_number', 1)} "
                    f"(estimated saving "
                    f"{saved:,.0f})."
                )

        return days

    # =========================================================
    # ROUTE OPTIMIZATION
    # =========================================================

    def _optimize_day_route(
        self,
        day_num: int,
        activities: List[Dict[str, Any]],
        adjustments: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Order activities for minimal geographical
        travel while keeping confirmed bookings
        at their fixed positions.
        """

        if len(activities) <= 2:
            return activities

        fixed_indices = {
            index
            for index, activity in enumerate(
                activities
            )
            if self._is_confirmed_booking(
                activity
            )
        }

        if len(fixed_indices) == len(
            activities
        ):
            return activities

        initial_dist = (
            self._calculate_route_distance(
                activities
            )
        )

        flexible_items = [
            activity
            for index, activity in enumerate(
                activities
            )
            if index not in fixed_indices
        ]

        # Exhaustive search for small days.
        if len(flexible_items) <= 6:

            best_order = flexible_items
            best_dist = float("inf")

            for permutation in itertools.permutations(
                flexible_items
            ):

                candidate_day = []

                flexible_index = 0

                for index in range(
                    len(activities)
                ):

                    if index in fixed_indices:

                        candidate_day.append(
                            activities[index]
                        )

                    else:

                        candidate_day.append(
                            permutation[
                                flexible_index
                            ]
                        )

                        flexible_index += 1

                distance = (
                    self._calculate_route_distance(
                        candidate_day
                    )
                )

                if distance < best_dist:

                    best_dist = distance

                    best_order = list(
                        permutation
                    )

            reordered = []

            flexible_index = 0

            for index in range(
                len(activities)
            ):

                if index in fixed_indices:

                    reordered.append(
                        activities[index]
                    )

                else:

                    reordered.append(
                        best_order[
                            flexible_index
                        ]
                    )

                    flexible_index += 1

            if best_dist < initial_dist:

                saved = round(
                    initial_dist
                    - best_dist,
                    2,
                )

                adjustments.append(
                    f"Day {day_num} route "
                    f"reordering: Reduced travel "
                    f"by {saved} km "
                    f"({initial_dist:.1f} km -> "
                    f"{best_dist:.1f} km)."
                )

                return reordered

        return activities

    # =========================================================
    # TIME SCHEDULING
    # =========================================================

    def _reschedule_day_times(
        self,
        day_num: int,
        activities: List[Dict[str, Any]],
        adjustments: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Build a safe chronological schedule for one day.

        Features:
        - Preserves activity duration.
        - Respects opening hours.
        - Never moves flexible activities backwards.
        - Adds realistic travel time.
        - Adds waiting time.
        - Preserves confirmed bookings.
        - Detects opening-hours conflicts.
        """

        if not activities:
            return []

        rescheduled: List[
            Dict[str, Any]
        ] = []

        current_time_m = (
            _time_to_minutes(
                self.default_day_start
            )
        )

        for i, act in enumerate(
            activities
        ):

            act_copy = dict(act)

            venue = self._get_venue(
                act_copy
            )

            act_name = (
                act_copy.get(
                    "activity_name"
                )
                or act_copy.get(
                    "title"
                )
                or (
                    venue.get("name")
                    if venue
                    else f"Activity {i + 1}"
                )
            )

            # -------------------------------------------------
            # CONFIRMED BOOKING
            # -------------------------------------------------

            if (
                self._is_confirmed_booking(
                    act_copy
                )
                and act_copy.get(
                    "start_time"
                )
            ):

                locked_start = (
                    _time_to_minutes(
                        act_copy[
                            "start_time"
                        ]
                    )
                )

                duration_value = (
                    act_copy.get(
                        "duration",
                        venue.get(
                            "duration_minutes",
                            90,
                        )
                        if venue
                        else 90,
                    )
                )

                dur_m = (
                    _parse_duration_minutes(
                        duration_value
                    )
                )

                if dur_m <= 0:
                    dur_m = 90

                current_time_m = (
                    locked_start
                )

                end_m = (
                    current_time_m
                    + dur_m
                )

                act_copy[
                    "activity_name"
                ] = act_name

                act_copy[
                    "start_time"
                ] = _minutes_to_time(
                    current_time_m
                )

                act_copy[
                    "end_time"
                ] = _minutes_to_time(
                    end_m
                )

                act_copy[
                    "duration"
                ] = f"{dur_m} mins"

                act_copy[
                    "travel_time"
                ] = (
                    "0 mins"
                    if i == 0
                    else act_copy.get(
                        "travel_time",
                        f"{self.min_buffer_mins} mins",
                    )
                )

                act_copy[
                    "schedule_status"
                ] = "Confirmed"

                current_time_m = end_m

                rescheduled.append(
                    act_copy
                )

                continue

            # -------------------------------------------------
            # ACTIVITY DURATION
            # -------------------------------------------------

            duration_value = (
                act_copy.get(
                    "duration",
                    venue.get(
                        "duration_minutes",
                        90,
                    )
                    if venue
                    else 90,
                )
            )

            dur_m = (
                _parse_duration_minutes(
                    duration_value
                )
            )

            if dur_m <= 0:
                dur_m = 90

            # -------------------------------------------------
            # TRAVEL
            # -------------------------------------------------

            transit_m = 0
            transit_type = "Walking"

            if (
                i > 0
                and len(rescheduled) > 0
            ):

                previous_activity = (
                    rescheduled[-1]
                )

                prev_venue = (
                    self._get_venue(
                        previous_activity
                    )
                )

                if prev_venue and venue:

                    lat1 = prev_venue.get(
                        "latitude"
                    )
                    lon1 = prev_venue.get(
                        "longitude"
                    )

                    lat2 = venue.get(
                        "latitude"
                    )
                    lon2 = venue.get(
                        "longitude"
                    )

                    if None not in (
                        lat1,
                        lon1,
                        lat2,
                        lon2,
                    ):

                        distance_km = (
                            haversine_distance_km(
                                lat1,
                                lon1,
                                lat2,
                                lon2,
                            )
                        )

                        transit_m = (
                            self._compute_transit_time(
                                distance_km
                            )
                        )

                        transit_type = (
                            self._get_transport_mode(
                                distance_km
                            )
                        )

                    else:

                        transit_m = (
                            self.min_buffer_mins
                        )

                        transit_type = (
                            "Local Transit"
                        )

                else:

                    transit_m = (
                        self.min_buffer_mins
                    )

                    transit_type = (
                        "Local Transit"
                    )

            current_time_m += (
                transit_m
            )

            # -------------------------------------------------
            # OPENING HOURS
            # -------------------------------------------------

            if venue:

                open_str = (
                    venue.get(
                        "opening_time"
                    )
                    or "09:00"
                )

                close_str = (
                    venue.get(
                        "closing_time"
                    )
                    or "19:00"
                )

            else:

                open_str = "09:00"
                close_str = "19:00"

            open_m = _time_to_minutes(
                open_str
            )

            close_m = _time_to_minutes(
                close_str
            )

            is_24h = (
                (
                    open_m == 0
                    and close_m >= 1439
                )
                or open_m == close_m
            )

            waiting_m = 0

            # -------------------------------------------------
            # OPENING ALIGNMENT
            # -------------------------------------------------

            if not is_24h:

                if current_time_m < open_m:

                    waiting_m = (
                        open_m
                        - current_time_m
                    )

                    current_time_m = (
                        open_m
                    )

                    adjustments.append(
                        f"Day {day_num}: "
                        f"Waited {waiting_m} mins "
                        f"for '{act_name}' "
                        f"to open."
                    )

                # Check whether full duration fits.
                available_m = (
                    close_m
                    - current_time_m
                )

                if (
                    available_m
                    < dur_m
                ):

                    act_copy[
                        "schedule_status"
                    ] = (
                        "Opening-hours conflict"
                    )

                    act_copy[
                        "schedule_warning"
                    ] = (
                        f"'{act_name}' requires "
                        f"{dur_m} mins but only "
                        f"{max(0, available_m)} "
                        f"mins remain before "
                        f"closing at "
                        f"{close_str}."
                    )

                    adjustments.append(
                        f"Day {day_num}: "
                        f"Opening-hours conflict "
                        f"for '{act_name}'. "
                        f"Full duration of "
                        f"{dur_m} mins does not "
                        f"fit before "
                        f"{close_str}."
                    )

                else:

                    act_copy[
                        "schedule_status"
                    ] = "Scheduled"

            else:

                act_copy[
                    "schedule_status"
                ] = "Scheduled"

            # -------------------------------------------------
            # FINAL SLOT
            # -------------------------------------------------

            start_m = current_time_m

            end_m = (
                current_time_m
                + dur_m
            )

            act_copy[
                "activity_name"
            ] = act_name

            act_copy[
                "category"
            ] = self._get_activity_category(
                act_copy
            )

            act_copy[
                "start_time"
            ] = _minutes_to_time(
                start_m
            )

            act_copy[
                "end_time"
            ] = _minutes_to_time(
                end_m
            )

            act_copy[
                "duration"
            ] = f"{dur_m} mins"

            act_copy[
                "travel_time"
            ] = f"{transit_m} mins"

            act_copy[
                "transportation"
            ] = transit_type

            act_copy[
                "opening_time"
            ] = open_str

            act_copy[
                "closing_time"
            ] = close_str

            act_copy[
                "waiting_time"
            ] = f"{waiting_m} mins"

            current_time_m = end_m

            rescheduled.append(
                act_copy
            )

        return rescheduled


# =============================================================
# FUNCTIONAL WRAPPER
# =============================================================

def optimize_itinerary(
    days: List[Dict[str, Any]],
    total_budget: float,
    travelers: int = 1,
    interests: Optional[List[str]] = None,
    candidates_map: Optional[
        Dict[str, Dict[str, Any]]
    ] = None,
) -> Tuple[
    List[Dict[str, Any]],
    Dict[str, Any],
]:
    """
    Convenience functional wrapper to run
    the ItineraryOptimizer.
    """

    optimizer = ItineraryOptimizer(
        total_budget=total_budget,
        travelers=travelers,
        interests=interests,
        candidates_map=candidates_map,
    )

    return optimizer.optimize(days)