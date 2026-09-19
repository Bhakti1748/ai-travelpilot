"""
Geographic & Transportation Tools:
4. calculate_distance
5. estimate_travel_time
"""

import math
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.services.dataset_service import (
    get_activity,
    get_transportation_routes,
    haversine_distance_km,
)
from app.tools.registry import default_tool_registry


# --- 4. calculate_distance ---
class CalculateDistanceInput(BaseModel):
    origin_activity_id: Optional[str] = Field(None, description="Activity ID of origin venue (e.g. 'act-paris-001')")
    dest_activity_id: Optional[str] = Field(None, description="Activity ID of destination venue (e.g. 'act-paris-002')")
    origin_lat: Optional[float] = Field(None, description="Origin latitude if not using activity ID")
    origin_lon: Optional[float] = Field(None, description="Origin longitude if not using activity ID")
    dest_lat: Optional[float] = Field(None, description="Destination latitude if not using activity ID")
    dest_lon: Optional[float] = Field(None, description="Destination longitude if not using activity ID")


def calculate_distance(
    origin_activity_id: Optional[str] = None,
    dest_activity_id: Optional[str] = None,
    origin_lat: Optional[float] = None,
    origin_lon: Optional[float] = None,
    dest_lat: Optional[float] = None,
    dest_lon: Optional[float] = None,
) -> Dict[str, Any]:
    """Calculate the precise geodesic distance between two locations or activities."""
    # Resolve origin coords
    origin_name = "Custom Origin"
    if origin_activity_id:
        act = get_activity(origin_activity_id)
        if not act:
            raise ValueError(f"Origin activity '{origin_activity_id}' not found.")
        origin_lat = act["latitude"]
        origin_lon = act["longitude"]
        origin_name = act["name"]

    # Resolve destination coords
    dest_name = "Custom Destination"
    if dest_activity_id:
        act = get_activity(dest_activity_id)
        if not act:
            raise ValueError(f"Destination activity '{dest_activity_id}' not found.")
        dest_lat = act["latitude"]
        dest_lon = act["longitude"]
        dest_name = act["name"]

    if None in (origin_lat, origin_lon, dest_lat, dest_lon):
        raise ValueError("Must provide either valid activity IDs or explicit (latitude, longitude) coordinates for both points.")

    dist_km = haversine_distance_km(origin_lat, origin_lon, dest_lat, dest_lon)
    dist_miles = round(dist_km * 0.621371, 3)

    return {
        "origin": origin_name,
        "destination": dest_name,
        "distance_km": dist_km,
        "distance_miles": dist_miles,
        "is_walking_distance": dist_km <= 1.8,
    }


# --- 5. estimate_travel_time ---
class EstimateTravelTimeInput(BaseModel):
    origin: str = Field(..., description="Origin name, address, or activity ID (e.g. 'act-paris-001' or 'Eiffel Tower')")
    destination: str = Field(..., description="Destination name, address, or activity ID (e.g. 'act-paris-002' or 'Musée du Louvre')")
    transport_type: Optional[str] = Field(None, description="Preferred mode: 'Walking', 'Metro', 'RER', 'Bus', 'Taxi'")


def estimate_travel_time(
    origin: str,
    destination: str,
    transport_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Estimate travel duration, transit options, and costs between two locations in Paris."""
    # Resolve names if IDs passed
    orig_act = get_activity(origin)
    orig_name = orig_act["name"] if orig_act else origin

    dest_act = get_activity(destination)
    dest_name = dest_act["name"] if dest_act else destination

    # 1. Check direct mock transportation dataset
    routes = get_transportation_routes(origin=orig_name, destination=dest_name)
    if not routes:
        # Try reversed lookup if undirected
        routes = get_transportation_routes(origin=dest_name, destination=orig_name)

    if routes:
        if transport_type:
            filtered = [r for r in routes if r["transport_type"].lower() == transport_type.lower()]
            if filtered:
                routes = filtered

        best = routes[0]
        return {
            "origin": orig_name,
            "destination": dest_name,
            "transport_type": best["transport_type"],
            "duration_minutes": best["duration_minutes"],
            "estimated_cost": best["estimated_cost"],
            "currency": "INR",
            "source": "verified_transit_schedule",
            "all_available_options": routes,
        }

    # 2. If no direct schedule, calculate based on physical distance
    if orig_act and dest_act:
        dist_km = haversine_distance_km(
            orig_act["latitude"], orig_act["longitude"], dest_act["latitude"], dest_act["longitude"]
        )
    else:
        dist_km = 3.5  # average Paris inter-arrondissement distance

    # Compute realistic times
    mode = transport_type or ("Walking" if dist_km <= 1.2 else "Metro")

    if mode.lower() == "walking":
        # Average 4.5 km/h
        duration = max(5, round((dist_km / 4.5) * 60))
        cost = 0.0
    elif mode.lower() in ("metro", "rer"):
        # 5 min wait + 25 km/h travel time
        duration = max(10, round(5 + (dist_km / 25.0) * 60))
        cost = 210.0
    elif mode.lower() == "taxi":
        # 5 min dispatch + 18 km/h city traffic
        duration = max(8, round(5 + (dist_km / 18.0) * 60))
        cost = round(600 + dist_km * 180, 0)
    else:
        # Bus
        duration = max(12, round(8 + (dist_km / 15.0) * 60))
        cost = 210.0

    return {
        "origin": orig_name,
        "destination": dest_name,
        "transport_type": mode,
        "distance_km": round(dist_km, 2),
        "duration_minutes": duration,
        "estimated_cost": cost,
        "currency": "INR",
        "source": "geodesic_urban_routing_model",
    }


# Register tools in default registry
default_tool_registry.register(
    name="calculate_distance",
    description="Calculate exact straight-line distance (km and miles) between two activities or coordinates.",
    parameters_schema=CalculateDistanceInput.model_json_schema(),
    func=calculate_distance,
    input_model=CalculateDistanceInput,
)

default_tool_registry.register(
    name="estimate_travel_time",
    description="Estimate transit duration, recommended transportation mode, and cost between two destinations.",
    parameters_schema=EstimateTravelTimeInput.model_json_schema(),
    func=estimate_travel_time,
    input_model=EstimateTravelTimeInput,
)
