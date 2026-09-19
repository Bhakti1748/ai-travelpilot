"""
Unit tests for TravelPilot AI Trip Planner Agent & Validation Layer:
- Itinerary generation with dataset candidates
- Invalid data detection & auto-repair (unknown IDs, overlaps, opening hours)
- Budget limits enforcement & replacement
- JSON structure verification
"""

import json
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.trip_planner import ItineraryValidator, plan_itinerary
from app.services.dataset_service import _dataset


def test_itinerary_generation():
    print("\n--- Test 1: Standard Itinerary Generation ---")
    result = plan_itinerary(
        destination="Paris",
        start_date="2026-10-10",
        end_date="2026-10-14",
        budget=100000.0,
        travelers=2,
        interests=["History", "Food", "Photography", "Museums"],
        travel_style="Balanced",
        transportation_preference="Metro & Walking",
    )

    assert result["success"] is True, "Plan generation failed"
    assert result["total_days"] == 5, f"Expected 5 days, got {result['total_days']}"
    assert len(result["days"]) == 5, f"Expected 5 day groups, got {len(result['days'])}"

    all_dataset_ids = {a["id"] for a in _dataset.all_activities}
    total_cost = 0

    required_fields = [
        "date",
        "start_time",
        "end_time",
        "activity_id",
        "activity_name",
        "location",
        "duration",
        "estimated_cost",
        "travel_time",
        "transportation",
        "reason",
    ]

    for day in result["days"]:
        assert len(day["activities"]) >= 3, f"Expected >=3 activities in day {day['day_number']}"
        for act in day["activities"]:
            for field in required_fields:
                assert field in act, f"Missing field '{field}' in activity"
            # Verify activity exists in real dataset
            assert (
                act["activity_id"] in all_dataset_ids
            ), f"Activity ID '{act['activity_id']}' is not in the dataset!"
            total_cost += act["estimated_cost"]

    assert total_cost <= result["total_budget"], "Total cost must not exceed budget"
    print(f"[OK] 5-day Paris itinerary generated with {len(result['days'])} days and total cost {total_cost} INR.")
    print(f"[OK] Planner engine: {result['planner_engine']}. Validation: {result['validation_status']}.")


def test_invalid_data_auto_repair():
    print("\n--- Test 2: Invalid Data Auto-Repair Layer ---")
    candidates_map = {a["id"]: a for a in _dataset.all_activities}
    validator = ItineraryValidator(
        candidates_map=candidates_map,
        total_budget=50000.0,
        travelers=2,
        default_travel_time_mins=20,
    )

    # Construct invalid day with:
    # 1. Unknown activity ID
    # 2. Overlapping times (starts before previous ends)
    # 3. Before opening hours (06:00 when opens at 09:00)
    invalid_days = [
        {
            "day_number": 1,
            "date": "2026-10-10",
            "activities": [
                {
                    "activity_id": "act-fake-nonexistent-123",  # Invalid ID!
                    "start_time": "06:00",  # Invalid early time!
                    "end_time": "08:00",
                },
                {
                    "activity_id": "act-paris-001",  # Louvre (opens 09:00)
                    "start_time": "07:30",  # Overlaps with previous & before open!
                    "end_time": "10:30",
                },
            ],
        }
    ]

    repaired_days, repairs = validator.validate_and_repair(invalid_days)

    assert len(repairs) > 0, "Validator should have reported repairs"
    repaired_acts = repaired_days[0]["activities"]

    # Verify ID replaced
    assert (
        repaired_acts[0]["activity_id"] in candidates_map
    ), "Fake activity ID should be replaced with real dataset candidate"

    # Verify opening hours respected
    louvre_act = repaired_acts[1]
    assert louvre_act["start_time"] >= "09:00", "Louvre must not start before 09:00"

    # Verify no overlap
    t0_end = repaired_acts[0]["end_time"]
    t1_start = repaired_acts[1]["start_time"]
    assert t1_start >= t0_end, f"Overlap not resolved: {t1_start} < {t0_end}"

    print(f"[OK] Successfully caught and auto-repaired {len(repairs)} invalid constraints:")
    for r in repairs:
        print(f"   - {r}")


def test_budget_limits_enforcement():
    print("\n--- Test 3: Budget Limits Enforcement & Replacement ---")
    candidates_map = {a["id"]: a for a in _dataset.all_activities}

    # Set strict budget of only 1,000 INR
    strict_budget = 1000.0
    validator = ItineraryValidator(
        candidates_map=candidates_map,
        total_budget=strict_budget,
        travelers=1,
    )

    # High-cost activity (Eiffel Tower Summit: 3100 INR, Louvre: 2200 INR)
    expensive_days = [
        {
            "day_number": 1,
            "date": "2026-10-10",
            "activities": [
                {
                    "activity_id": "act-paris-002",  # Eiffel Tower (3100 INR)
                    "start_time": "10:00",
                    "end_time": "12:30",
                },
                {
                    "activity_id": "act-paris-001",  # Louvre (2200 INR)
                    "start_time": "14:00",
                    "end_time": "17:00",
                },
            ],
        }
    ]

    repaired_days, repairs = validator.validate_and_repair(expensive_days)

    total_cost = sum(
        act["estimated_cost"] for d in repaired_days for act in d["activities"]
    )
    assert (
        total_cost <= strict_budget
    ), f"Repaired cost ({total_cost}) must be <= strict budget ({strict_budget})"

    print(f"[OK] Enforced budget ceiling: original cost (5,300 INR) reduced to {total_cost} INR <= {strict_budget} INR.")
    for r in repairs:
        print(f"   - {r}")


def test_json_structure_verification():
    print("\n--- Test 4: JSON Structure & Schema Verification ---")
    result = plan_itinerary(
        destination="Paris",
        start_date="2026-10-11",
        end_date="2026-10-12",
        budget=40000.0,
        travelers=2,
        interests=["Art", "Nature"],
        travel_style="Relaxed",
        transportation_preference="Walking",
    )

    # Ensure serializable to valid JSON
    json_str = json.dumps(result, indent=2)
    parsed = json.loads(json_str)

    assert parsed["success"] is True
    assert "days" in parsed
    assert "total_estimated_spending" in parsed
    assert "remaining_budget" in parsed
    assert parsed["total_days"] == 2

    print("[OK] JSON serialization and structure verified completely.")


def run_all_tests():
    print("==================================================")
    print("RUNNING TRAVELPILOT AI TRIP PLANNER TEST SUITE")
    print("==================================================")
    test_itinerary_generation()
    test_invalid_data_auto_repair()
    test_budget_limits_enforcement()
    test_json_structure_verification()
    print("\n==================================================")
    print("ALL AI TRIP PLANNER TESTS PASSED! (100% Verified)")
    print("==================================================")


if __name__ == "__main__":
    run_all_tests()
