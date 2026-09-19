"""
Unit tests for TravelPilot Agent Tool Layer.
Verifies all 12 tools, input/output schemas, ToolRegistry execution, and error handling.
"""

import os
import sys

# Ensure backend directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import Base, SessionLocal, engine
from app.services.travel_service import seed_database
from app.tools import default_tool_registry


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()



def test_registry_registration():
    print("\n--- Test: Tool Registry Registration ---")
    registered_tools = default_tool_registry.list_tools()
    registered_names = {t["name"] for t in registered_tools}
    print(f"Registered tools count: {len(registered_names)}")
    print(f"Tools: {sorted(list(registered_names))}")

    expected_tools = [
        "search_activities",
        "get_activity_details",
        "find_nearby_activities",
        "calculate_distance",
        "estimate_travel_time",
        "check_opening_hours",
        "calculate_activity_cost",
        "get_current_itinerary",
        "detect_schedule_conflicts",
        "calculate_trip_budget",
        "find_alternatives",
        "update_itinerary",
    ]

    for tool in expected_tools:
        assert tool in registered_names, f"Tool '{tool}' is missing from registry!"
        # Verify schema is populated
        t_def = default_tool_registry.get(tool)
        assert t_def is not None
        assert "properties" in t_def.parameters_schema, f"Schema missing properties for '{tool}'"

    # Verify Gemini declaration formatting
    gemini_decls = default_tool_registry.to_gemini_declarations()
    assert len(gemini_decls) == len(expected_tools)
    print("[PASS] All 12 tools registered with valid Gemini schemas.")


def test_tool_search_activities():
    print("\n--- Test Tool 1: search_activities ---")
    # Search by category and cost
    res = default_tool_registry.execute("search_activities", category="Museum", max_cost=2500)
    assert res["success"] is True, f"Execution failed: {res['error']}"
    data = res["result"]
    assert data["total_matches"] > 0
    assert all("Museum" in act["category"] for act in data["activities"])
    assert all(act["estimated_cost"] <= 2500 for act in data["activities"])

    # Search by keyword
    res2 = default_tool_registry.execute("search_activities", query="Eiffel")
    assert res2["success"] is True
    assert res2["result"]["total_matches"] >= 1
    assert "Eiffel" in res2["result"]["activities"][0]["name"]
    print(f"[PASS] search_activities returned {res2['result']['total_matches']} match(es) for 'Eiffel'.")


def test_tool_get_activity_details():
    print("\n--- Test Tool 2: get_activity_details ---")
    res = default_tool_registry.execute("get_activity_details", activity_id="act-paris-001")
    assert res["success"] is True
    assert res["result"]["found"] is True
    assert res["result"]["activity"]["name"] == "Musée du Louvre"

    # Non-existent ID should return success=False safely contained
    res_missing = default_tool_registry.execute("get_activity_details", activity_id="non-existent-999")
    assert res_missing["success"] is False
    assert "does not exist" in res_missing["error"]
    print("[PASS] get_activity_details works for existing and contains missing IDs.")


def test_tool_find_nearby_activities():
    print("\n--- Test Tool 3: find_nearby_activities ---")
    # Louvre coordinates: 48.8606, 2.3376
    res = default_tool_registry.execute(
        "find_nearby_activities",
        latitude=48.8606,
        longitude=2.3376,
        radius_km=3.0,
        limit=5,
    )
    assert res["success"] is True
    data = res["result"]
    assert data["count"] > 0
    assert len(data["activities"]) <= 5
    # Nearby activities should be sorted by distance
    distances = [a["distance_km"] for a in data["activities"]]
    assert distances == sorted(distances)
    print(f"[PASS] find_nearby_activities found {data['count']} within 3km of Louvre coordinates.")


def test_tool_calculate_distance():
    print("\n--- Test Tool 4: calculate_distance ---")
    # Louvre to Eiffel Tower
    res = default_tool_registry.execute(
        "calculate_distance",
        origin_activity_id="act-paris-001",
        dest_activity_id="act-paris-002",
    )
    assert res["success"] is True
    data = res["result"]
    assert 2.5 <= data["distance_km"] <= 4.0
    print(f"[PASS] calculate_distance Louvre to Eiffel: {data['distance_km']} km.")


def test_tool_estimate_travel_time():
    print("\n--- Test Tool 5: estimate_travel_time ---")
    res_metro = default_tool_registry.execute(
        "estimate_travel_time",
        origin="act-paris-001",
        destination="act-paris-002",
        transport_type="Metro",
    )
    assert res_metro["success"] is True
    assert res_metro["result"]["duration_minutes"] > 0
    assert res_metro["result"]["estimated_cost"] >= 0

    res_walk = default_tool_registry.execute(
        "estimate_travel_time",
        origin="act-paris-001",
        destination="act-paris-002",
        transport_type="Walking",
    )
    assert res_walk["success"] is True
    # Walking duration should take longer than metro for ~3km
    assert res_walk["result"]["duration_minutes"] > res_metro["result"]["duration_minutes"]
    print(f"[PASS] estimate_travel_time: Metro {res_metro['result']['duration_minutes']}m, Walking {res_walk['result']['duration_minutes']}m.")


def test_tool_check_opening_hours():
    print("\n--- Test Tool 6: check_opening_hours ---")
    # Louvre is open 09:00 - 18:00
    res_open = default_tool_registry.execute(
        "check_opening_hours",
        activity_id="act-paris-001",
        time="10:00",
        duration_minutes=90,
    )
    assert res_open["success"] is True
    assert res_open["result"]["is_open"] is True
    assert res_open["result"]["fits_duration"] is True

    # Louvre at 22:00 should be closed
    res_closed = default_tool_registry.execute(
        "check_opening_hours",
        activity_id="act-paris-001",
        time="22:00",
    )
    assert res_closed["success"] is True
    assert res_closed["result"]["is_open"] is False
    print("[PASS] check_opening_hours correctly determined open and closed hours.")


def test_tool_calculate_activity_cost():
    print("\n--- Test Tool 7: calculate_activity_cost ---")
    # 2 travelers, 10% discount on Louvre (2200 INR base cost)
    res = default_tool_registry.execute(
        "calculate_activity_cost",
        activity_id="act-paris-001",
        travelers=2,
        discount_percent=10.0,
    )
    assert res["success"] is True
    data = res["result"]
    assert data["unit_cost"] == 2200.0
    assert data["subtotal"] == 4400.0
    assert data["discount_amount"] == 440.0
    assert data["total_cost"] == 3960.0
    print(f"[PASS] calculate_activity_cost total: {data['total_cost']} INR (subtotal {data['subtotal']}).")



def test_tool_get_current_itinerary():
    print("\n--- Test Tool 8: get_current_itinerary ---")
    trip_id = "trip-paris-demo-2026"
    res = default_tool_registry.execute("get_current_itinerary", trip_id=trip_id)
    assert res["success"] is True
    data = res["result"]
    assert data["trip_id"] == trip_id
    assert "Paris" in data["destination"]
    assert len(data["days"]) > 0
    day_1 = data["days"][0]
    assert len(day_1["items"]) > 0
    print(f"[PASS] get_current_itinerary retrieved {data['total_items']} items across {len(data['days'])} days.")



def test_tool_detect_schedule_conflicts():
    print("\n--- Test Tool 9: detect_schedule_conflicts ---")
    trip_id = "trip-paris-demo-2026"
    res = default_tool_registry.execute("detect_schedule_conflicts", trip_id=trip_id)
    assert res["success"] is True
    data = res["result"]
    assert "conflicts_found" in data
    assert "conflicts" in data
    assert "recommendations" in data
    print(f"[PASS] detect_schedule_conflicts completed. Conflicts found: {data['total_conflicts']}.")


def test_tool_calculate_trip_budget():
    print("\n--- Test Tool 10: calculate_trip_budget ---")
    trip_id = "trip-paris-demo-2026"
    res = default_tool_registry.execute("calculate_trip_budget", trip_id=trip_id)
    assert res["success"] is True
    data = res["result"]
    assert data["total_budget"] > 0
    assert data["total_spent"] > 0
    assert data["remaining_budget"] == data["total_budget"] - data["total_spent"]
    assert data["spending_status"] in ["on_track", "warning", "exceeded"]
    print(f"[PASS] calculate_trip_budget: Spent {data['total_spent']} of {data['total_budget']} ({data['spending_status']}).")


def test_tool_find_alternatives():
    print("\n--- Test Tool 11: find_alternatives ---")
    res = default_tool_registry.execute(
        "find_alternatives",
        activity_id="act-paris-001",
        reason="Crowded or disruption at Eiffel Tower",
        limit=3,
    )
    assert res["success"] is True
    data = res["result"]
    assert len(data["alternatives"]) > 0
    assert data["original_activity"]["id"] == "act-paris-001"
    top_alt = data["alternatives"][0]
    assert "name" in top_alt
    assert "relevance_score" in top_alt
    print(f"[PASS] find_alternatives found {len(data['alternatives'])} alternatives. Top: '{top_alt['name']}'.")



def test_tool_update_itinerary():
    print("\n--- Test Tool 12: update_itinerary (add, reschedule, replace, remove) ---")
    trip_id = "trip-paris-demo-2026"

    # 1. Add
    res_add = default_tool_registry.execute(
        "update_itinerary",
        trip_id=trip_id,
        action="add",
        day_number=1,
        time="17:00",
        activity_id="act-paris-010",
        notes="Added for evening leisure",
    )
    assert res_add["success"] is True, f"Add failed: {res_add['error']}"
    item_id = res_add["result"]["affected_item"]["id"]
    print(f"[PASS] Added item '{item_id}' to Day 1.")

    # 2. Reschedule
    res_resched = default_tool_registry.execute(
        "update_itinerary",
        trip_id=trip_id,
        action="reschedule",
        item_id=item_id,
        day_number=2,
        time="18:30",
    )
    assert res_resched["success"] is True
    print(f"[PASS] Rescheduled item '{item_id}' to Day 2 at 18:30.")

    # 3. Replace
    res_replace = default_tool_registry.execute(
        "update_itinerary",
        trip_id=trip_id,
        action="replace",
        item_id=item_id,
        activity_id="act-paris-004",  # Notre-Dame
    )
    assert res_replace["success"] is True
    assert "Notre-Dame" in res_replace["result"]["affected_item"]["new_title"]
    print(f"[PASS] Replaced item '{item_id}' with Notre-Dame.")

    # 4. Remove
    res_remove = default_tool_registry.execute(
        "update_itinerary",
        trip_id=trip_id,
        action="remove",
        item_id=item_id,
    )
    assert res_remove["success"] is True
    print(f"[PASS] Removed test item '{item_id}'.")


def test_tool_error_containment():
    print("\n--- Test: Tool Error Containment ---")
    # Calling non-existent tool
    res_missing = default_tool_registry.execute("unknown_tool_xyz")
    assert res_missing["success"] is False
    assert "not registered" in res_missing["error"]

    # Calling tool with invalid parameter types (Pydantic validation error)
    res_invalid = default_tool_registry.execute("calculate_activity_cost", travelers="not-an-integer")
    assert res_invalid["success"] is False
    assert "Execution failed" in res_invalid["error"]
    print("[PASS] Error containment works properly for unregistered tools and validation failures.")


if __name__ == "__main__":
    init_db()
    print("==================================================")
    print("RUNNING TRAVELPILOT AGENT TOOL LAYER TEST SUITE")
    print("==================================================")
    test_registry_registration()
    test_tool_search_activities()
    test_tool_get_activity_details()
    test_tool_find_nearby_activities()
    test_tool_calculate_distance()
    test_tool_estimate_travel_time()
    test_tool_check_opening_hours()
    test_tool_calculate_activity_cost()
    test_tool_get_current_itinerary()
    test_tool_detect_schedule_conflicts()
    test_tool_calculate_trip_budget()
    test_tool_find_alternatives()
    test_tool_update_itinerary()
    test_tool_error_containment()
    print("\n==================================================")
    print("ALL 12 AGENT TOOLS & REGISTRY TESTS PASSED [OK]")
    print("==================================================")
