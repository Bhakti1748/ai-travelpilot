"""
Unit tests for TravelPilot dataset service functions:
- search_activities()
- get_activity()
- find_nearby_activities()
- filter_by_interest()
- filter_by_budget()
- filter_by_time()
- get_transportation_routes()
"""

import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.dataset_service import (
    filter_by_budget,
    filter_by_interest,
    filter_by_time,
    find_nearby_activities,
    get_activity,
    get_transportation_routes,
    haversine_distance_km,
    search_activities,
)


def test_dataset_loading():
    print("\n--- Test: Dataset Loading ---")
    activities = search_activities()
    print(f"Total activities loaded: {len(activities)}")
    assert len(activities) >= 25, f"Expected at least 25 activities, got {len(activities)}"

    sample = activities[0]
    required_keys = [
        "id",
        "name",
        "category",
        "description",
        "latitude",
        "longitude",
        "estimated_cost",
        "duration_minutes",
        "opening_time",
        "closing_time",
        "rating",
        "interests",
        "suitable_for",
        "address",
    ]
    for key in required_keys:
        assert key in sample, f"Missing required key '{key}' in activity"
    print("[OK] Dataset loading verified with all required fields present.")


def test_search_activities():
    print("\n--- Test: search_activities() ---")
    # 1. Free-text search
    louvre_results = search_activities(query="Louvre")
    assert len(louvre_results) >= 1, "Expected at least 1 result for 'Louvre'"
    assert "Louvre" in louvre_results[0]["name"]
    print(f"[OK] Free-text search found: {louvre_results[0]['name']}")

    # 2. Category search
    museums = search_activities(category="Museum")
    assert len(museums) >= 3, f"Expected at least 3 Museum activities, got {len(museums)}"
    for m in museums:
        assert m["category"].lower() == "museum"
    print(f"[OK] Category search found {len(museums)} museums.")

    # 3. Rating threshold search
    top_rated = search_activities(min_rating=4.8)
    assert len(top_rated) > 0, "Expected activities with rating >= 4.8"
    for tr in top_rated:
        assert tr["rating"] >= 4.8
    print(f"[OK] Rating filter found {len(top_rated)} activities with rating >= 4.8.")


def test_get_activity():
    print("\n--- Test: get_activity() ---")
    act = get_activity("act-paris-001")
    assert act is not None, "Expected to find activity 'act-paris-001'"
    assert act["name"] == "Musée du Louvre"
    assert act["category"] == "Museum"

    # Non-existent
    none_act = get_activity("act-non-existent-999")
    assert none_act is None, "Expected None for non-existent ID"
    print("[OK] get_activity() works for existing and non-existent IDs.")


def test_find_nearby_activities():
    print("\n--- Test: find_nearby_activities() ---")
    # Coordinates of Notre-Dame (lat: 48.852968, lon: 2.349902)
    nd_lat, nd_lon = 48.852968, 2.349902

    # Find within 1.5 km radius
    nearby = find_nearby_activities(nd_lat, nd_lon, radius_km=1.5, limit=5)
    assert len(nearby) > 0, "Expected nearby activities around Notre-Dame"
    assert nearby[0]["id"] == "act-paris-004", "Notre-Dame should be closest to itself (distance ~0)"
    assert nearby[0]["distance_km"] <= 0.05

    # Check sorting
    for i in range(len(nearby) - 1):
        assert nearby[i]["distance_km"] <= nearby[i + 1]["distance_km"], "Results should be sorted by distance"

    print(f"[OK] Nearby activities around Notre-Dame (radius 1.5km):")
    for n in nearby:
        print(f"   - {n['name']} ({n['distance_km']} km away)")


def test_filter_by_interest():
    print("\n--- Test: filter_by_interest() ---")
    # Filter by single interest
    food_acts = filter_by_interest("Food")
    assert len(food_acts) >= 4, f"Expected at least 4 Food activities, got {len(food_acts)}"
    for f in food_acts:
        assert any("food" in i.lower() for i in f["interests"])

    # Filter by multiple interests
    history_or_photo = filter_by_interest(["History", "Photography"])
    assert len(history_or_photo) >= 10, f"Expected >=10 activities, got {len(history_or_photo)}"
    print(f"[OK] Filter by interest found {len(food_acts)} food activities and {len(history_or_photo)} history/photo activities.")


def test_filter_by_budget():
    print("\n--- Test: filter_by_budget() ---")
    # Free activities
    free_acts = filter_by_budget(max_cost=0)
    assert len(free_acts) >= 5, f"Expected at least 5 free activities, got {len(free_acts)}"
    for act in free_acts:
        assert act["estimated_cost"] == 0

    # Under 1500 INR
    budget_acts = filter_by_budget(max_cost=1500)
    assert len(budget_acts) >= len(free_acts)
    for act in budget_acts:
        assert act["estimated_cost"] <= 1500
    print(f"[OK] Budget filter found {len(free_acts)} completely free activities and {len(budget_acts)} activities <= 1500 INR.")


def test_filter_by_time():
    print("\n--- Test: filter_by_time() ---")
    # Morning: 08:30
    morning_acts = filter_by_time("08:30")
    assert len(morning_acts) > 0, "Expected open activities at 08:30"
    for act in morning_acts:
        assert act["opening_time"] <= "08:30" <= act["closing_time"]

    # Afternoon: 14:00 (peak hours, almost all should be open)
    afternoon_acts = filter_by_time("14:00")
    assert len(afternoon_acts) >= 20, f"Expected >=20 activities open at 14:00, got {len(afternoon_acts)}"

    # Late Night: 22:00
    night_acts = filter_by_time("22:00")
    assert len(night_acts) > 0, "Expected night venues to be open"
    for act in night_acts:
        assert act["opening_time"] <= "22:00" <= act["closing_time"]
    print(f"[OK] Time filter verified: 08:30 ({len(morning_acts)} open), 14:00 ({len(afternoon_acts)} open), 22:00 ({len(night_acts)} open).")


def test_transportation_data():
    print("\n--- Test: Transportation Data ---")
    routes = get_transportation_routes(origin="Eiffel Tower")
    assert len(routes) > 0, "Expected routes from Eiffel Tower"
    for r in routes:
        assert "eiffel tower" in r["origin"].lower()
        assert "transport_type" in r
        assert "duration_minutes" in r
        assert "estimated_cost" in r
    print(f"[OK] Found {len(routes)} transportation options originating from Eiffel Tower.")


def run_all_tests():
    print("================================================")
    print("RUNNING TRAVELPILOT DATASET SERVICE TEST SUITE")
    print("================================================")
    test_dataset_loading()
    test_search_activities()
    test_get_activity()
    test_find_nearby_activities()
    test_filter_by_interest()
    test_filter_by_budget()
    test_filter_by_time()
    test_transportation_data()
    print("\n================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! (100% Deterministic Local)")
    print("================================================")


if __name__ == "__main__":
    run_all_tests()
