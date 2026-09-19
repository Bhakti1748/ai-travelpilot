"""
Unit and Integration Tests for TravelPilot Itinerary Constraint & Optimization Engine
Tests:
- All 7 functions in constraint_engine.py
- Route clustering and distance reduction in itinerary_optimizer.py
- Preserving confirmed bookings
- Budget cap enforcement
- Deduplication
- Full planning pipeline: Generate -> Validate -> Optimize -> Validate again -> Return
"""

import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import Base, SessionLocal, engine
from app.services.constraint_engine import (
    audit_itinerary_constraints,
    calculate_daily_cost,
    calculate_total_cost,
    detect_budget_conflicts,
    detect_duplicate_activities,
    detect_opening_hour_conflicts,
    detect_time_conflicts,
    detect_travel_time_conflicts,
)
from app.services.dataset_service import dataset_service
from app.services.itinerary_optimizer import ItineraryOptimizer, optimize_itinerary
from app.services.travel_service import seed_database
from app.agents.trip_planner import plan_itinerary


def setup_module():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()


def test_detect_time_conflicts():
    print("\n--- Test 1: detect_time_conflicts ---")
    # Fixture with direct overlap
    overlapping_activities = [
        {
            "activity_id": "act-paris-001",
            "activity_name": "Musée du Louvre",
            "start_time": "09:30",
            "end_time": "12:00",
            "duration": "150 mins",
        },
        {
            "activity_id": "act-paris-003",
            "activity_name": "Musée d'Orsay",
            "start_time": "11:30",  # Starts before Louvre ends!
            "end_time": "13:30",
            "duration": "120 mins",
        },
    ]

    conflicts = detect_time_conflicts(overlapping_activities)
    assert len(conflicts) > 0
    assert any(c["type"] == "overlap" for c in conflicts)
    assert conflicts[0]["overlap_minutes"] == 30
    print(f"[PASS] Successfully detected direct overlap ({conflicts[0]['overlap_minutes']}m).")

    # Fixture without overlap
    spaced_activities = [
        {
            "activity_id": "act-paris-001",
            "activity_name": "Musée du Louvre",
            "start_time": "09:30",
            "end_time": "11:30",
        },
        {
            "activity_id": "act-paris-003",
            "activity_name": "Musée d'Orsay",
            "start_time": "12:15",
            "end_time": "14:15",
        },
    ]
    no_overlap = detect_time_conflicts(spaced_activities, min_gap_mins=15)
    assert len(no_overlap) == 0
    print("[PASS] Spaced activities flagged 0 time conflicts.")


def test_detect_opening_hour_conflicts():
    print("\n--- Test 2: detect_opening_hour_conflicts ---")
    # Louvre hours: 09:00 - 18:00
    early_activity = [
        {
            "activity_id": "act-paris-001",
            "activity_name": "Musée du Louvre",
            "start_time": "07:30",  # Opens at 09:00
            "end_time": "10:30",
        }
    ]
    early_conflicts = detect_opening_hour_conflicts(early_activity)
    assert len(early_conflicts) == 1
    assert early_conflicts[0]["type"] == "before_opening"
    print(f"[PASS] Caught opening hours violation: {early_conflicts[0]['description']}")

    late_activity = [
        {
            "activity_id": "act-paris-001",
            "activity_name": "Musée du Louvre",
            "start_time": "17:00",
            "end_time": "19:30",  # Closes at 18:00
        }
    ]
    late_conflicts = detect_opening_hour_conflicts(late_activity)
    assert len(late_conflicts) == 1
    assert late_conflicts[0]["type"] == "after_closing"
    print(f"[PASS] Caught closing hours violation: {late_conflicts[0]['description']}")


def test_detect_budget_conflicts():
    print("\n--- Test 3: detect_budget_conflicts ---")
    activities = [
        {"activity_id": "act-paris-001", "estimated_cost": 2200.0, "title": "Louvre"},
        {"activity_id": "act-paris-002", "estimated_cost": 3100.0, "title": "Eiffel"},
        {"activity_id": "act-paris-006", "estimated_cost": 1600.0, "title": "Palace"},
    ]
    # Total for 2 travelers = (2200 + 3100 + 1600) * 2 = 13,800 INR

    # Case A: Budget of 10,000 INR (Over budget by 3,800)
    conflict_res = detect_budget_conflicts(activities, total_budget=10000.0, travelers=2)
    assert conflict_res["has_conflict"] is True
    assert conflict_res["total_cost"] == 13800.0
    assert conflict_res["excess_amount"] == 3800.0
    print(f"[PASS] Budget conflict detected: excess {conflict_res['excess_amount']} INR.")

    # Case B: Budget of 20,000 INR (Under budget)
    ok_res = detect_budget_conflicts(activities, total_budget=20000.0, travelers=2)
    assert ok_res["has_conflict"] is False
    assert ok_res["excess_amount"] == 0.0
    print(f"[PASS] Within budget validated: {ok_res['total_cost']} of {ok_res['total_budget']} INR.")


def test_detect_travel_time_conflicts():
    print("\n--- Test 4: detect_travel_time_conflicts ---")
    # Eiffel Tower (act-paris-002) to Louvre (act-paris-001) is ~3.2km.
    # Metro takes ~15-20 mins. Only 5 mins buffer scheduled:
    tight_transit = [
        {
            "activity_id": "act-paris-002",
            "activity_name": "Eiffel Tower",
            "start_time": "09:30",
            "end_time": "11:30",
        },
        {
            "activity_id": "act-paris-001",
            "activity_name": "Musée du Louvre",
            "start_time": "11:35",  # 5 mins later
            "end_time": "14:00",
        },
    ]

    conflicts = detect_travel_time_conflicts(tight_transit)
    assert len(conflicts) == 1
    assert conflicts[0]["type"] == "travel_time_deficit"
    assert conflicts[0]["distance_km"] > 2.5
    print(f"[PASS] Detected travel deficit: {conflicts[0]['description']}")


def test_detect_duplicate_activities():
    print("\n--- Test 5: detect_duplicate_activities ---")
    days = [
        {
            "day_number": 1,
            "activities": [
                {"activity_id": "act-paris-001", "activity_name": "Musée du Louvre", "start_time": "09:30"},
                {"activity_id": "act-paris-003", "activity_name": "Musée d'Orsay", "start_time": "14:00"},
            ],
        },
        {
            "day_number": 2,
            "activities": [
                {"activity_id": "act-paris-001", "activity_name": "Musée du Louvre", "start_time": "10:00"},  # Duplicate!
                {"activity_id": "act-paris-002", "activity_name": "Eiffel Tower", "start_time": "15:00"},
            ],
        },
    ]

    dup_conflicts = detect_duplicate_activities(days)
    assert len(dup_conflicts) == 1
    assert dup_conflicts[0]["activity_id"] == "act-paris-001"
    print(f"[PASS] Duplicate activity detected across days: {dup_conflicts[0]['description']}")


def test_calculate_costs():
    print("\n--- Test 6: calculate_daily_cost and calculate_total_cost ---")
    day_acts = [
        {"estimated_cost": 2200.0},
        {"estimated_cost": 1800.0},
        {"estimated_cost": 0.0},
    ]
    daily = calculate_daily_cost(day_acts, travelers=2)
    assert daily == 8000.0

    days = [
        {"activities": [{"estimated_cost": 1000.0}, {"estimated_cost": 500.0}]},
        {"activities": [{"estimated_cost": 2000.0}]},
    ]
    total = calculate_total_cost(days, travelers=2)
    # (1500 + 2000) * 2 = 7000.0
    assert total == 7000.0
    print(f"[PASS] Daily ({daily} INR) and Total ({total} INR) cost calculations verified.")


def test_optimizer_geographic_clustering():
    print("\n--- Test 7: ItineraryOptimizer Geographic Route Ordering ---")
    # Deliberately scrambled order on Day 1:
    # 1. Eiffel Tower (West, lon 2.294) (act-paris-002)
    # 2. Marché d'Aligre (Far East, lon 2.378) (act-paris-018)
    # 3. Musée Rodin (West/Center, lon 2.315) (act-paris-007)
    # Zigzags West (Eiffel) -> Far East (Aligre) -> Back to West (Rodin)!
    scrambled_activities = [
        {"activity_id": "act-paris-002", "activity_name": "Eiffel Tower", "duration": "120 mins"},
        {"activity_id": "act-paris-018", "activity_name": "Marché d'Aligre", "duration": "90 mins"},
        {"activity_id": "act-paris-007", "activity_name": "Musée Rodin", "duration": "100 mins"},
    ]

    days = [{"day_number": 1, "activities": scrambled_activities}]
    optimizer = ItineraryOptimizer(total_budget=50000.0, travelers=1)

    optimized_days, metrics = optimizer.optimize(days)
    opt_acts = optimized_days[0]["activities"]

    print(f"Initial distance: {metrics['initial_distance_km']} km")
    print(f"Optimized distance: {metrics['optimized_distance_km']} km")
    print(f"Distance saved: {metrics['distance_saved_km']} km")

    assert metrics["optimized_distance_km"] < metrics["initial_distance_km"]
    assert metrics["distance_saved_km"] > 0
    print("[PASS] Geographic clustering reordered activities to minimize unnecessary transit.")



def test_optimizer_preserves_confirmed_bookings():
    print("\n--- Test 8: ItineraryOptimizer Preserves Confirmed Bookings ---")
    # Day with a locked hotel checkout / reservation
    mixed_activities = [
        {"activity_id": "act-paris-001", "activity_name": "Musée du Louvre", "duration": "120 mins"},
        {
            "id": "book-train-fixed",
            "activity_name": "Eurostar Paris to London",
            "is_booking": True,
            "status": "Confirmed",
            "start_time": "14:00",
            "duration": "120 mins",
        },
        {"activity_id": "act-paris-002", "activity_name": "Eiffel Tower", "duration": "120 mins"},
    ]

    days = [{"day_number": 1, "activities": mixed_activities}]
    optimizer = ItineraryOptimizer(total_budget=50000.0, travelers=1)

    optimized_days, _ = optimizer.optimize(days)
    opt_acts = optimized_days[0]["activities"]

    # Booking must stay at position 1 (second item) and keep its 14:00 start time
    booking_item = [a for a in opt_acts if a.get("is_booking")][0]
    assert booking_item["start_time"] == "14:00"
    assert booking_item["id"] == "book-train-fixed"
    print("[PASS] Confirmed booking preserved intact with locked schedule.")


def test_optimizer_budget_cap_enforcement():
    print("\n--- Test 9: ItineraryOptimizer Budget Cap Enforcement ---")
    expensive_activities = [
        {"activity_id": "act-paris-002", "estimated_cost": 3100.0, "activity_name": "Eiffel Tower"},
        {"activity_id": "act-paris-006", "estimated_cost": 1600.0, "activity_name": "Palace of Versailles"},
        {"activity_id": "act-paris-001", "estimated_cost": 2200.0, "activity_name": "Musée du Louvre"},
    ]
    # Total cost = 6900 INR. Set budget to 2500 INR!
    days = [{"day_number": 1, "activities": expensive_activities}]
    optimizer = ItineraryOptimizer(total_budget=2500.0, travelers=1)

    optimized_days, metrics = optimizer.optimize(days)
    final_cost = metrics["final_total_cost"]

    assert final_cost <= 2500.0
    print(f"[PASS] Optimizer brought total cost from 6,900 to {final_cost} INR (under 2,500 INR budget).")


def test_full_pipeline_generate_validate_optimize():
    print("\n--- Test 10: Full Pipeline (Generate -> Validate -> Optimize -> Validate again) ---")
    result = plan_itinerary(
        destination="Paris",
        start_date="2026-10-10",
        end_date="2026-10-12",
        budget=40000.0,
        travelers=2,
        interests=["History", "Photography", "Food"],
        travel_style="Balanced",
        transportation_preference="Metro",
    )

    assert result["success"] is True
    assert result["total_days"] == 3
    assert "optimization_metrics" in result
    assert "constraint_audit" in result

    audit = result["constraint_audit"]
    assert audit["has_budget_conflict"] is False
    print(f"[PASS] 3-Day Paris itinerary planned with {result['total_estimated_spending']} INR.")
    print(f"[PASS] Optimization Metrics: Distance saved: {result['optimization_metrics']['distance_saved_km']} km, Travel time saved: {result['optimization_metrics']['travel_time_saved_mins']} mins.")
    print(f"[PASS] Final constraint audit is_valid: {audit['is_valid']}, total conflicts: {audit['total_conflicts']}.")


if __name__ == "__main__":
    setup_module()
    print("==================================================================")
    print("RUNNING TRAVELPILOT CONSTRAINT & OPTIMIZER TEST SUITE")
    print("==================================================================")
    test_detect_time_conflicts()
    test_detect_opening_hour_conflicts()
    test_detect_budget_conflicts()
    test_detect_travel_time_conflicts()
    test_detect_duplicate_activities()
    test_calculate_costs()
    test_optimizer_geographic_clustering()
    test_optimizer_preserves_confirmed_bookings()
    test_optimizer_budget_cap_enforcement()
    test_full_pipeline_generate_validate_optimize()
    print("\n==================================================================")
    print("ALL 10 CONSTRAINT & OPTIMIZATION ENGINE TESTS PASSED [OK]")
    print("==================================================================")
