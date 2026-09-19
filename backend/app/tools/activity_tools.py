"""
Activity-related Agent Tools:
1. search_activities
2. get_activity_details
3. find_nearby_activities
4. find_alternatives
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.services.dataset_service import (
    _dataset,
    find_nearby_activities as dataset_find_nearby,
    get_activity as dataset_get_activity,
    search_activities as dataset_search,
)
from app.tools.registry import default_tool_registry


# --- 1. search_activities ---
class SearchActivitiesInput(BaseModel):
    query: Optional[str] = Field(None, description="Free-text search query matching name, description, address, or tags")
    category: Optional[str] = Field(None, description="Category filter (e.g. Museum, Food, Historical, Nature, Shopping, Entertainment, Walking)")
    min_rating: Optional[float] = Field(None, ge=1.0, le=5.0, description="Minimum visitor rating (1.0 to 5.0)")
    max_cost: Optional[float] = Field(None, ge=0.0, description="Maximum estimated cost in INR")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of results to return")


def search_activities(
    query: Optional[str] = None,
    category: Optional[str] = None,
    min_rating: Optional[float] = None,
    max_cost: Optional[float] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Search available attractions and experiences by query, category, rating, or budget."""
    raw_results = dataset_search(query=query, category=category, min_rating=min_rating)

    if max_cost is not None:
        raw_results = [r for r in raw_results if r.get("estimated_cost", 0.0) <= max_cost]

    limited = raw_results[:limit]
    return {
        "count": len(limited),
        "total_matches": len(raw_results),
        "activities": [
            {
                "id": a["id"],
                "name": a["name"],
                "category": a["category"],
                "estimated_cost": a["estimated_cost"],
                "rating": a["rating"],
                "duration_minutes": a["duration_minutes"],
                "address": a["address"],
                "opening_time": a["opening_time"],
                "closing_time": a["closing_time"],
                "interests": a.get("interests", []),
            }
            for a in limited
        ],
    }


# --- 2. get_activity_details ---
class GetActivityDetailsInput(BaseModel):
    activity_id: str = Field(..., description="Unique ID of the activity (e.g. 'act-paris-001')")


def get_activity_details(activity_id: str) -> Dict[str, Any]:
    """Retrieve comprehensive details, coordinates, operating hours, and pricing for an activity."""
    act = dataset_get_activity(activity_id.strip())
    if not act:
        raise ValueError(f"Activity with ID '{activity_id}' does not exist in dataset.")
    return {"found": True, "activity": act}


# --- 3. find_nearby_activities ---
class FindNearbyActivitiesInput(BaseModel):
    latitude: float = Field(..., description="Starting latitude coordinate")
    longitude: float = Field(..., description="Starting longitude coordinate")
    radius_km: float = Field(3.0, gt=0.0, le=25.0, description="Search radius in kilometers")
    limit: int = Field(5, ge=1, le=20, description="Max activities to return")
    category: Optional[str] = Field(None, description="Optional category filter")


def find_nearby_activities(
    latitude: float,
    longitude: float,
    radius_km: float = 3.0,
    limit: int = 5,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """Discover venues and points of interest within a geographic radius from coordinates."""
    results = dataset_find_nearby(latitude, longitude, radius_km=radius_km, limit=None)

    if category:
        cat_lower = category.strip().lower()
        results = [r for r in results if r.get("category", "").lower() == cat_lower]

    limited = results[:limit]
    return {
        "center_coordinates": {"latitude": latitude, "longitude": longitude},
        "radius_km": radius_km,
        "count": len(limited),
        "activities": [
            {
                "id": a["id"],
                "name": a["name"],
                "category": a["category"],
                "distance_km": a.get("distance_km"),
                "estimated_cost": a["estimated_cost"],
                "rating": a["rating"],
                "address": a["address"],
            }
            for a in limited
        ],
    }


# --- 11. find_alternatives ---
class FindAlternativesInput(BaseModel):
    activity_id: str = Field(..., description="ID of the activity to replace (e.g. 'act-paris-001')")
    reason: Optional[str] = Field(None, description="Reason for replacement: 'closed', 'expensive', 'crowded', 'bad_weather', or general")
    max_cost: Optional[float] = Field(None, ge=0.0, description="Cost ceiling for the alternative")
    radius_km: float = Field(4.0, gt=0.0, le=20.0, description="Proximity radius around the original activity")
    limit: int = Field(4, ge=1, le=10, description="Max recommendations to return")


def find_alternatives(
    activity_id: str,
    reason: Optional[str] = None,
    max_cost: Optional[float] = None,
    radius_km: float = 4.0,
    limit: int = 4,
) -> Dict[str, Any]:
    """Find smart substitute activities matching category, proximity, or budget when a plan is disrupted."""
    target = dataset_get_activity(activity_id.strip())
    if not target:
        raise ValueError(f"Target activity with ID '{activity_id}' not found.")

    target_cat = target.get("category", "")
    target_interests = set(i.lower() for i in target.get("interests", []))
    target_lat = target.get("latitude", 48.8566)
    target_lon = target.get("longitude", 2.3522)

    # Search nearby
    nearby = dataset_find_nearby(target_lat, target_lon, radius_km=radius_km, limit=None)

    candidates = []
    for cand in nearby:
        if cand["id"] == activity_id:
            continue

        if max_cost is not None and cand.get("estimated_cost", 0.0) > max_cost:
            continue

        # If reason is bad_weather or rain, prefer indoor venues
        if reason and "weather" in reason.lower() and cand.get("category") == "Nature":
            continue

        cand_interests = set(i.lower() for i in cand.get("interests", []))
        shared_interests = target_interests.intersection(cand_interests)

        # Relevance score
        score = 0
        if cand.get("category") == target_cat:
            score += 3
        score += len(shared_interests) * 1.5
        score += (5.0 - min(5.0, cand.get("distance_km", 0.0))) * 0.5
        score += cand.get("rating", 4.0) * 0.5

        cand_copy = dict(cand)
        cand_copy["relevance_score"] = round(score, 2)
        candidates.append(cand_copy)

    candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
    top_alternatives = candidates[:limit]

    return {
        "original_activity": {
            "id": target["id"],
            "name": target["name"],
            "category": target["category"],
            "estimated_cost": target["estimated_cost"],
        },
        "reason": reason or "Alternative requested",
        "alternatives_count": len(top_alternatives),
        "alternatives": [
            {
                "id": a["id"],
                "name": a["name"],
                "category": a["category"],
                "distance_km": a.get("distance_km"),
                "estimated_cost": a["estimated_cost"],
                "rating": a["rating"],
                "address": a["address"],
                "relevance_score": a["relevance_score"],
            }
            for a in top_alternatives
        ],
    }


# Register tools in default registry
default_tool_registry.register(
    name="search_activities",
    description="Search activities in the destination by query, category, minimum rating, or maximum budget.",
    parameters_schema=SearchActivitiesInput.model_json_schema(),
    func=search_activities,
    input_model=SearchActivitiesInput,
)

default_tool_registry.register(
    name="get_activity_details",
    description="Retrieve full details, GPS coordinates, operating hours, and cost for a specific activity ID.",
    parameters_schema=GetActivityDetailsInput.model_json_schema(),
    func=get_activity_details,
    input_model=GetActivityDetailsInput,
)

default_tool_registry.register(
    name="find_nearby_activities",
    description="Find venues and points of interest within a given kilometer radius from GPS coordinates.",
    parameters_schema=FindNearbyActivitiesInput.model_json_schema(),
    func=find_nearby_activities,
    input_model=FindNearbyActivitiesInput,
)

default_tool_registry.register(
    name="find_alternatives",
    description="Find smart alternative activities in the same category or nearby when a venue is closed, crowded, or over budget.",
    parameters_schema=FindAlternativesInput.model_json_schema(),
    func=find_alternatives,
    input_model=FindAlternativesInput,
)
