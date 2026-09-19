"""
TravelPilot Dataset Service
Loads and searches the local Paris travel and transportation datasets deterministically.
"""

import json
import math
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from app.services.places_services import search_places

# Resolve dataset paths relative to the project structure
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Navigate from backend/app/services to root/data
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
ACTIVITIES_FILE = os.path.join(DATA_DIR, "paris_activities.json")
TRANSPORT_FILE = os.path.join(DATA_DIR, "paris_transportation.json")


class TravelDataset:
    """Singleton-style dataset manager for deterministic local access."""

    def __init__(
        self,
        activities_path: str = ACTIVITIES_FILE,
        transport_path: str = TRANSPORT_FILE,
    ):
        self.activities_path = activities_path
        self.transport_path = transport_path
        self._activities: List[Dict[str, Any]] = []
        self._activities_by_id: Dict[str, Dict[str, Any]] = {}
        self._transportation: List[Dict[str, Any]] = []
        self.reload()

    def reload(self) -> None:
        """Loads or reloads JSON data from disk."""
        if os.path.exists(self.activities_path):
            with open(self.activities_path, "r", encoding="utf-8") as f:
                self._activities = json.load(f)
                self._activities_by_id = {act["id"]: act for act in self._activities}
        else:
            self._activities = []
            self._activities_by_id = {}

        if os.path.exists(self.transport_path):
            with open(self.transport_path, "r", encoding="utf-8") as f:
                self._transportation = json.load(f)
        else:
            self._transportation = []

    @property
    def all_activities(self) -> List[Dict[str, Any]]:
        return list(self._activities)

    @property
    def all_transportation(self) -> List[Dict[str, Any]]:
        return list(self._transportation)

    def get_activity(self, activity_id: str) -> Optional[Dict[str, Any]]:
        return self._activities_by_id.get(activity_id)

    def find_nearby_activities(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 3.0,
        limit: Optional[int] = 5,
    ) -> List[Dict[str, Any]]:
        return find_nearby_activities(latitude, longitude, radius_km, limit)

    def search_activities(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        min_rating: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        return search_activities(query, category, min_rating)




# Global default instance
_dataset = TravelDataset()
dataset_service = _dataset



def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates great-circle distance between two geographic coordinates in kilometers.
    Uses the Haversine formula.
    """
    R = 6371.0  # Earth radius in kilometers

    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 3)


# --- Core Required Functions ---


def search_activities(
    query: Optional[str] = None,
    category: Optional[str] = None,
    min_rating: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Search activities by free-text query (matches name, description, address),
    category, and minimum rating threshold.
    """
    results = _dataset.all_activities

    if category:
        cat_lower = category.strip().lower()
        results = [
            act for act in results if act.get("category", "").lower() == cat_lower
        ]

    if min_rating is not None:
        results = [
            act for act in results if float(act.get("rating", 0.0)) >= min_rating
        ]

    if query:
        q_lower = query.strip().lower()
        results = [
            act
            for act in results
            if q_lower in act.get("name", "").lower()
            or q_lower in act.get("description", "").lower()
            or q_lower in act.get("address", "").lower()
            or any(q_lower in interest.lower() for interest in act.get("interests", []))
        ]

    return results


def get_activity(activity_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve an activity by its unique identifier."""
    return _dataset._activities_by_id.get(activity_id)


def find_nearby_activities(
    latitude: float,
    longitude: float,
    radius_km: float = 3.0,
    limit: Optional[int] = 5,
) -> List[Dict[str, Any]]:
    """
    Finds activities within a geographic radius (in km) from given latitude/longitude.
    Returns results sorted by increasing distance, annotated with 'distance_km'.
    """
    nearby = []
    for act in _dataset.all_activities:
        act_lat = act.get("latitude")
        act_lon = act.get("longitude")
        if act_lat is None or act_lon is None:
            continue

        dist = haversine_distance_km(latitude, longitude, act_lat, act_lon)
        if dist <= radius_km:
            act_copy = dict(act)
            act_copy["distance_km"] = dist
            nearby.append(act_copy)

    # Sort by closest distance first
    nearby.sort(key=lambda x: x["distance_km"])

    if limit is not None:
        return nearby[:limit]
    return nearby


def filter_by_interest(interests: Union[str, List[str]]) -> List[Dict[str, Any]]:
    """
    Filter activities that match any of the specified interests (case-insensitive).
    """
    if isinstance(interests, str):
        target_interests = {interests.strip().lower()}
    else:
        target_interests = {i.strip().lower() for i in interests if i.strip()}

    if not target_interests:
        return _dataset.all_activities

    results = []
    for act in _dataset.all_activities:
        act_interests = {i.lower() for i in act.get("interests", [])}
        if target_interests.intersection(act_interests):
            results.append(act)

    return results


def filter_by_budget(max_cost: float) -> List[Dict[str, Any]]:
    """
    Filter activities where estimated_cost <= max_cost.
    Results are sorted by cost ascending (free activities first).
    """
    results = [
        act for act in _dataset.all_activities if act.get("estimated_cost", 0.0) <= max_cost
    ]
    results.sort(key=lambda x: x.get("estimated_cost", 0.0))
    return results


def filter_by_time(time_str: str) -> List[Dict[str, Any]]:
    """
    Filter activities that are open at the specified time of day.
    Accepts time in 'HH:MM' (24-hour format), e.g. '14:30', '09:00', '21:00'.
    """
    # Normalize input
    try:
        t_parsed = datetime.strptime(time_str.strip(), "%H:%M").time()
    except ValueError:
        raise ValueError(
            f"Invalid time format '{time_str}'. Expected 'HH:MM' in 24-hour format (e.g. '14:30')."
        )

    results = []
    for act in _dataset.all_activities:
        open_str = act.get("opening_time")
        close_str = act.get("closing_time")
        if not open_str or not close_str:
            continue

        try:
            open_t = datetime.strptime(open_str, "%H:%M").time()
            close_t = datetime.strptime(close_str, "%H:%M").time()

            # Normal opening hours (e.g. 09:00 to 18:00)
            if open_t <= close_t:
                if open_t <= t_parsed <= close_t:
                    results.append(act)
            else:
                # Overnight span (e.g. 19:00 to 02:00)
                if t_parsed >= open_t or t_parsed <= close_t:
                    results.append(act)
        except Exception:
            continue

    return results


def get_transportation_routes(
    origin: Optional[str] = None, destination: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Lookup mock transit options between origin and destination.
    """
    routes = _dataset.all_transportation
    if origin:
        orig_lower = origin.strip().lower()
        routes = [r for r in routes if orig_lower in r.get("origin", "").lower()]
    if destination:
        dest_lower = destination.strip().lower()
        routes = [
            r for r in routes if dest_lower in r.get("destination", "").lower()
        ]
    return routes

async def get_activities_for_destination(
    destination: str,
    categories: Optional[List[str]] = None,
    query: Optional[str] = None,
    min_rating: Optional[float] = None,
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """
    Get activities for a destination using Geoapify.

    Falls back to the existing local Paris dataset if
    the external API cannot provide results.
    """

    if not destination or not destination.strip():
        return search_activities(
            query=query,
            min_rating=min_rating,
        )

    # Default categories for TravelPilot.
    if not categories:
        categories = [
            "museum",
            "food",
            "historical",
            "nature",
            "shopping",
            "entertainment",
        ]

    try:
        activities = await search_places(
            destination=destination.strip(),
            categories=categories,
            limit=limit,
        )

        if activities:
            # Apply optional rating filter.
            if min_rating is not None:
                activities = [
                    activity
                    for activity in activities
                    if float(activity.get("rating", 0.0))
                    >= min_rating
                ]

            # Apply optional text search.
            if query:
                query_lower = query.strip().lower()

                activities = [
                    activity
                    for activity in activities
                    if (
                        query_lower
                        in str(activity.get("name", "")).lower()
                        or query_lower
                        in str(activity.get("description", "")).lower()
                        or query_lower
                        in str(activity.get("address", "")).lower()
                    )
                ]

            return activities

    except Exception as exc:
        print(
            f"[TravelPilot] Geoapify lookup failed for "
            f"'{destination}': {exc}"
        )

    # Existing Paris dataset remains the fallback.
    print(
        f"[TravelPilot] Using local dataset fallback "
        f"for '{destination}'."
    )

    return search_activities(
        query=query,
        min_rating=min_rating,
    )