import os
from typing import List, Dict, Any

import httpx
from dotenv import load_dotenv
from app.services.currency_service import get_currency_for_country

load_dotenv()

GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")

BASE_URL = "https://api.geoapify.com/v2/places"


CATEGORY_MAP = {
    "museum": "entertainment.museum",
    "food": "catering.restaurant",
    "restaurant": "catering.restaurant",
    "shopping": "commercial.shopping_mall",
    "nature": "leisure.park",
    "entertainment": "entertainment",
    "historical": "tourism.sights",
}


def normalize_category(categories: List[str]) -> str:
    """
    Convert Geoapify categories into TravelPilot categories.
    """

    category_text = " ".join(categories).lower()

    if "museum" in category_text:
        return "Museum"

    if "restaurant" in category_text or "catering" in category_text:
        return "Food"

    if "historic" in category_text or "tourism.sights" in category_text:
        return "Historical"

    if "park" in category_text or "nature" in category_text:
        return "Nature"

    if "shopping" in category_text or "commercial" in category_text:
        return "Shopping"

    if "entertainment" in category_text:
        return "Entertainment"

    return "Other"


def get_interests_for_category(category: str) -> List[str]:
    """
    Convert TravelPilot category into relevant user interests.
    """

    mapping = {
        "Museum": ["Museums", "History", "Photography"],
        "Food": ["Food"],
        "Historical": ["History", "Photography"],
        "Nature": ["Nature", "Photography"],
        "Shopping": ["Shopping"],
        "Entertainment": ["Entertainment"],
    }

    return mapping.get(category, [])

def estimate_activity_cost(
    category: str,
    country: str,
) -> float:
    """
    Estimate activity cost based on destination country.

    These are approximate planning values only.
    They are NOT live prices.
    """

    cost_estimates = {
        "India": {
            "Museum": 300.0,
            "Food": 500.0,
            "Historical": 200.0,
            "Nature": 0.0,
            "Shopping": 1500.0,
            "Entertainment": 800.0,
            "Other": 400.0,
        },
        "Japan": {
            "Museum": 1000.0,
            "Food": 1500.0,
            "Historical": 500.0,
            "Nature": 0.0,
            "Shopping": 5000.0,
            "Entertainment": 3000.0,
            "Other": 1000.0,
        },
        "United Kingdom": {
            "Museum": 15.0,
            "Food": 25.0,
            "Historical": 10.0,
            "Nature": 0.0,
            "Shopping": 60.0,
            "Entertainment": 40.0,
            "Other": 20.0,
        },
        "France": {
            "Museum": 15.0,
            "Food": 25.0,
            "Historical": 10.0,
            "Nature": 0.0,
            "Shopping": 50.0,
            "Entertainment": 30.0,
            "Other": 20.0,
        },
        "United States": {
            "Museum": 20.0,
            "Food": 25.0,
            "Historical": 10.0,
            "Nature": 0.0,
            "Shopping": 60.0,
            "Entertainment": 40.0,
            "Other": 20.0,
        },
    }

    country_estimates = cost_estimates.get(
        country,
        cost_estimates["United States"],
    )

    return country_estimates.get(
        category,
        country_estimates["Other"],
    )

def estimate_activity_duration(category: str) -> int:
    """
    Estimate the typical time a traveler may spend
    at an activity.

    These are approximate planning values only.
    They are not exact opening or visit durations.
    """

    duration_map = {
        "Museum": 120,
        "Food": 75,
        "Historical": 60,
        "Nature": 90,
        "Shopping": 120,
        "Entertainment": 120,
        "Other": 90,
    }

    return duration_map.get(category, 90)

def deduplicate_activities(
    activities: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Remove duplicate or invalid activities.

    Two activities are considered duplicates when they have
    the same name and nearly identical coordinates.
    """

    seen = set()
    unique_activities = []

    for activity in activities:
        name = str(
            activity.get("name", "")
        ).strip().lower()

        latitude = activity.get("latitude")
        longitude = activity.get("longitude")

        # Skip invalid places
        if not name or name == "unnamed place":
            continue

        if latitude is None or longitude is None:
            continue

        try:
            latitude = round(float(latitude), 4)
            longitude = round(float(longitude), 4)
        except (TypeError, ValueError):
            continue

        # Create a unique key
        key = (
            name,
            latitude,
            longitude,
        )

        if key in seen:
            continue

        seen.add(key)
        unique_activities.append(activity)

    return unique_activities

async def geocode_destination(destination: str):
    """
    Convert a city name into latitude and longitude.
    """

    url = "https://api.geoapify.com/v1/geocode/search"

    params = {
        "text": destination,
        "format": "json",
        "limit": 1,
        "apiKey": GEOAPIFY_API_KEY,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()

    data = response.json()

    if not data.get("results"):
        raise ValueError(
            f"Destination not found: {destination}"
        )

    result = data["results"][0]

    return {
        "lat": result["lat"],
        "lon": result["lon"],
        "city": result.get("city", destination),
        "country": result.get("country"),
    }


async def search_places(
    destination: str,
    categories: List[str],
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Search places around a destination using Geoapify.
    """

    if not GEOAPIFY_API_KEY:
        raise RuntimeError(
            "GEOAPIFY_API_KEY is not configured"
        )

    location = await geocode_destination(destination)

    geo_categories = []

    for category in categories:
        mapped = CATEGORY_MAP.get(
            category.lower(),
            category,
        )
        geo_categories.append(mapped)

    params = {
        "categories": ",".join(geo_categories),
        "filter": (
            f"circle:{location['lon']},"
            f"{location['lat']},"
            f"15000"
        ),
        "bias": (
            f"proximity:{location['lon']},"
            f"{location['lat']}"
        ),
        "limit": limit,
        "apiKey": GEOAPIFY_API_KEY,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            BASE_URL,
            params=params,
        )
        response.raise_for_status()

    data = response.json()

    activities = []

    for feature in data.get("features", []):
        properties = feature.get("properties", {})

        # Convert Geoapify category into TravelPilot category.
        category = normalize_category(
            properties.get("categories", [])
        )

        country = properties.get(
            "country",
            destination,
        )

        currency = get_currency_for_country(country)

        activities.append(
            {
                "id": properties.get("place_id"),

                "name": properties.get(
                    "name"
                ) or "Unnamed place",

                "category": category,

                "description": properties.get(
                    "formatted",
                    "",
                ),

                "latitude": properties.get(
                    "lat"
                ),

                "longitude": properties.get(
                    "lon"
                ),

                "address": properties.get(
                    "formatted",
                    "",
                ),

                "city": properties.get(
                    "city",
                    destination,
                ),

                "country": country,

                "currency_code": currency["code"],

                "currency_symbol": currency["symbol"],

                "distance_meters": properties.get(
                    "distance"
                ),

                # Estimated planning values.
                "estimated_cost": estimate_activity_cost(
    category,
    country,
),

                "duration_minutes": estimate_activity_duration(category),

                # Opening hours will be added later
                # using a suitable place-details source.
                "opening_time": None,

                "closing_time": None,

                "rating": float(
                    properties.get(
                        "rating",
                        0.0,
                    ) or 0.0
                ),

                "interests": get_interests_for_category(
                    category
                ),
            }
        )

    return deduplicate_activities(activities)