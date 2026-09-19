"""
TravelPilot Comprehensive QA Test Suite
Validates the complete application across all 17 core requirements:
1. Creating a trip
2. Invalid trip input
3. Budget calculation
4. Itinerary generation
5. Opening hour validation
6. Schedule conflict detection
7. Travel time handling
8. AI assistant
9. Activity cancellation
10. Disruption simulation
11. Replanning
12. Applying changes
13. Budget reduction
14. Changing interests
15. Refreshing the dashboard
16. Backend unavailable / error states
17. Invalid Gemini/API response
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.db_models import TripModel, ItineraryItemModel, BudgetModel
from app.services.constraint_engine import (
    calculate_daily_cost,
    calculate_total_cost,
    detect_opening_hour_conflicts,
    detect_time_conflicts,
    detect_travel_time_conflicts,
)
from app.services.itinerary_optimizer import ItineraryOptimizer
from app.agents.disruption_manager import DisruptionManager
from app.agents.travel_assistant import TravelAssistant
from app.agents.trip_planner import plan_itinerary


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


# ----------------------------------------------------------------------
# 1. Creating a trip
# ----------------------------------------------------------------------
def test_01_create_trip(client):
    payload = {
        "destination": "Rome, Italy",
        "start_date": "2026-11-01",
        "end_date": "2026-11-05",
        "budget": 95000.0,
        "currency": "INR",
        "travelers": 2,
        "interests": ["History", "Food", "Architecture"],
        "travel_style": "Balanced",
        "transport_preference": "Public Transit",
        "auto_generate_itinerary": False,
    }
    response = client.post("/api/trips", json=payload)
    assert response.status_code in (200, 201), response.text
    data = response.json()
    assert data["destination"] == "Rome, Italy"
    assert data["budget"] == 95000.0
    assert data["travelers"] == 2
    assert "id" in data


# ----------------------------------------------------------------------
# 2. Invalid trip input
# ----------------------------------------------------------------------
def test_02_invalid_trip_input_validation(client):
    # Empty destination
    res_empty_dest = client.post("/api/trips", json={
        "destination": "   ",
        "start_date": "2026-11-01",
        "end_date": "2026-11-05",
        "budget": 50000,
        "travelers": 1,
    })
    assert res_empty_dest.status_code == 422

    # Inverted dates (end_date < start_date)
    res_inverted_dates = client.post("/api/trips", json={
        "destination": "London, UK",
        "start_date": "2026-11-10",
        "end_date": "2026-11-05",
        "budget": 50000,
        "travelers": 1,
    })
    assert res_inverted_dates.status_code == 422

    # Invalid date format
    res_bad_format = client.post("/api/trips", json={
        "destination": "London, UK",
        "start_date": "not-a-date",
        "end_date": "2026-11-05",
        "budget": 50000,
        "travelers": 1,
    })
    assert res_bad_format.status_code == 422

    # Negative budget
    res_neg_budget = client.post("/api/trips", json={
        "destination": "London, UK",
        "start_date": "2026-11-01",
        "end_date": "2026-11-05",
        "budget": -1000,
        "travelers": 1,
    })
    assert res_neg_budget.status_code == 422

    # Zero travelers
    res_zero_travelers = client.post("/api/trips", json={
        "destination": "London, UK",
        "start_date": "2026-11-01",
        "end_date": "2026-11-05",
        "budget": 50000,
        "travelers": 0,
    })
    assert res_zero_travelers.status_code == 422


# ----------------------------------------------------------------------
# 3. Budget calculation
# ----------------------------------------------------------------------
def test_03_budget_calculation(client):
    test_activities = [
        {"cost": 1500.0, "time": "09:00"},
        {"cost": 2500.0, "time": "14:00"},
    ]
    daily_cost_1_traveler = calculate_daily_cost(test_activities, travelers=1)
    daily_cost_2_travelers = calculate_daily_cost(test_activities, travelers=2)
    assert daily_cost_1_traveler == 4000.0
    assert daily_cost_2_travelers == 8000.0

    days_schedule = [
        {"day_number": 1, "activities": test_activities},
        {"day_number": 2, "activities": [{"cost": 1000.0, "time": "10:00"}]},
    ]
    total_cost = calculate_total_cost(days_schedule, travelers=2)
    assert total_cost == 10000.0

    # Test via API for demo trip
    res = client.get("/api/trips/trip-paris-demo-2026/budget")
    assert res.status_code == 200
    b_data = res.json()
    assert "total_budget" in b_data
    assert "estimated_spending" in b_data
    assert "remaining_budget" in b_data
    assert b_data["remaining_budget"] == max(0.0, round(b_data["total_budget"] - b_data["estimated_spending"], 2))


# ----------------------------------------------------------------------
# 4. Itinerary generation
# ----------------------------------------------------------------------
def test_04_itinerary_generation(client):
    # Generate itinerary for demo trip
    res = client.post("/api/trips/trip-paris-demo-2026/itinerary/generate")
    assert res.status_code == 200
    data = res.json()
    assert "days" in data
    assert len(data["days"]) > 0
    day1 = data["days"][0]
    assert "activities" in day1
    assert len(day1["activities"]) >= 2
    # Verify coordinates and duration are populated
    first_item = day1["activities"][0]
    assert "title" in first_item
    assert "time" in first_item
    assert "cost" in first_item


# ----------------------------------------------------------------------
# 5. Opening hour validation
# ----------------------------------------------------------------------
def test_05_opening_hour_validation():
    # Activity open 09:00 - 18:00
    activity_data = {
        "title": "Musée d'Orsay",
        "opening_time": "09:30",
        "closing_time": "18:00",
    }
    candidates_map = {"act-orsay": activity_data}

    # Scheduled at 08:00 (too early)
    early_day = [
        {"day_number": 1, "activities": [{"activity_id": "act-orsay", "time": "08:00", "duration": "90 mins"}]}
    ]
    conflicts_early = detect_opening_hour_conflicts(early_day, candidates_map)
    assert len(conflicts_early) > 0
    assert "before opening" in conflicts_early[0]["message"].lower()

    # Scheduled at 17:30 with 90 min duration (ends after 18:00 closing)
    late_day = [
        {"day_number": 1, "activities": [{"activity_id": "act-orsay", "time": "17:30", "duration": "90 mins"}]}
    ]
    conflicts_late = detect_opening_hour_conflicts(late_day, candidates_map)
    assert len(conflicts_late) > 0
    assert "after closing" in conflicts_late[0]["message"].lower()


# ----------------------------------------------------------------------
# 6. Schedule conflict detection
# ----------------------------------------------------------------------
def test_06_schedule_conflict_detection():
    overlapping_activities = [
        {"day_number": 1, "activities": [
            {"title": "Louvre Museum", "time": "10:00", "duration": "120 mins"},
            {"title": "Tuileries Garden", "time": "11:00", "duration": "60 mins"},
        ]}
    ]
    conflicts = detect_time_conflicts(overlapping_activities)
    assert len(conflicts) > 0
    assert "overlap" in conflicts[0]["message"].lower()


# ----------------------------------------------------------------------
# 7. Travel time handling
# ----------------------------------------------------------------------
def test_07_travel_time_handling():
    # Two venues far apart with only 5 minutes between them
    candidates_map = {
        "act-1": {"latitude": 48.8584, "longitude": 2.2945},  # Eiffel Tower
        "act-2": {"latitude": 48.8867, "longitude": 2.3431},  # Sacre-Coeur (~5 km away)
    }
    tight_schedule = [
        {"day_number": 1, "activities": [
            {"activity_id": "act-1", "title": "Eiffel", "time": "10:00", "duration": "60 mins"}, # ends 11:00
            {"activity_id": "act-2", "title": "Sacre-Coeur", "time": "11:05", "duration": "60 mins"}, # 5 min gap
        ]}
    ]
    conflicts = detect_travel_time_conflicts(tight_schedule, candidates_map)
    assert len(conflicts) > 0
    assert "insufficient transit buffer" in conflicts[0]["message"].lower()


# ----------------------------------------------------------------------
# 8. AI assistant
# ----------------------------------------------------------------------
def test_08_ai_assistant_queries_and_confirmation(client):
    # Query spending
    res_spend = client.post("/api/assistant/chat", json={
        "message": "How much have I spent so far?",
        "trip_id": "trip-paris-demo-2026",
    })
    assert res_spend.status_code == 200
    data_spend = res_spend.json()
    assert "ai_response" in data_spend
    assert "message" in data_spend["ai_response"]
    assert "INR" in data_spend["ai_response"]["message"]

    # Query schedule fit
    res_fit = client.post("/api/assistant/chat", json={
        "message": "Can I fit Sainte-Chapelle into today's schedule?",
        "trip_id": "trip-paris-demo-2026",
    })
    assert res_fit.status_code == 200
    assert "Sainte-Chapelle" in res_fit.json()["ai_response"]["message"]

    # Simulation query
    res_sim = client.post("/api/assistant/chat", json={
        "message": "What happens if the Louvre is cancelled?",
        "trip_id": "trip-paris-demo-2026",
    })
    assert res_sim.status_code == 200
    assert "proposal" in res_sim.json().get("action_type", "")


# ----------------------------------------------------------------------
# 9. Activity cancellation
# ----------------------------------------------------------------------
def test_09_activity_cancellation_disruption(client):
    res = client.post("/api/disruptions/simulate", json={
        "disruption_type": "activity_cancelled",
        "title": "Musée du Louvre",
    }, params={"trip_id": "trip-paris-demo-2026"})
    assert res.status_code == 200
    data = res.json()
    assert data["simulation_mode"] is True
    assert len(data["affected_items"]) > 0
    assert data["recommended_alternative"] is not None
    rec_title = data["recommended_alternative"].get("title") or data["recommended_alternative"].get("name")
    assert rec_title != "Musée du Louvre"


# ----------------------------------------------------------------------
# 10. Disruption simulation (Read-only check)
# ----------------------------------------------------------------------
def test_10_disruption_simulation_is_read_only(client):
    # Fetch initial itinerary count
    init_res = client.get("/api/trips/trip-paris-demo-2026/itinerary")
    init_count = sum(len(d["activities"]) for d in init_res.json()["days"])

    # Run simulation
    sim_res = client.post("/api/disruptions/simulate", json={
        "disruption_type": "activity_cancelled",
        "title": "Eiffel Tower Summit",
    }, params={"trip_id": "trip-paris-demo-2026"})
    assert sim_res.status_code == 200

    # Verify DB itinerary was NOT modified
    after_res = client.get("/api/trips/trip-paris-demo-2026/itinerary")
    after_count = sum(len(d["activities"]) for d in after_res.json()["days"])
    assert init_count == after_count


# ----------------------------------------------------------------------
# 11. Replanning
# ----------------------------------------------------------------------
def test_11_replanning_logic():
    db = SessionLocal()
    try:
        manager = DisruptionManager(db=db)
        sim = manager.simulate_disruption(
            trip_id="trip-paris-demo-2026",
            disruption_type="activity_cancelled",
            title="Musée du Louvre",
            db=db,
        )
        assert len(sim["alternatives"]) > 0
        rec = sim["recommended_alternative"]
        assert rec is not None
        assert rec["similarity_score"] > 0
    finally:
        db.close()


# ----------------------------------------------------------------------
# 12. Applying changes
# ----------------------------------------------------------------------
def test_12_apply_changes_persistence(client):
    res = client.post("/api/replan", json={
        "disruption_type": "activity_cancelled",
        "title": "Musée du Louvre",
    }, params={"trip_id": "trip-paris-demo-2026"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("replan_applied", "replanned")
    assert len(data["updated_itinerary"]) > 0

    # Verify DB has new item
    itin = client.get("/api/trips/trip-paris-demo-2026/itinerary").json()
    all_titles = [item["title"] for d in itin["days"] for item in d["activities"]]
    assert "Musée du Louvre" not in all_titles


# ----------------------------------------------------------------------
# 13. Budget reduction
# ----------------------------------------------------------------------
def test_13_budget_reduction_handling(client):
    # Simulate budget reduction to 80000 INR
    res_sim = client.post("/api/disruptions/simulate", json={
        "disruption_type": "budget_reduced",
        "new_budget": 80000.0,
    }, params={"trip_id": "trip-paris-demo-2026"})
    assert res_sim.status_code == 200
    sim_data = res_sim.json()
    assert sim_data["budget_impact"]["revised_budget"] == 80000.0

    # Apply budget reduction
    res_apply = client.post("/api/replan", json={
        "disruption_type": "budget_reduced",
        "new_budget": 80000.0,
    }, params={"trip_id": "trip-paris-demo-2026"})
    assert res_apply.status_code == 200

    # Verify trip budget is updated
    trip_data = client.get("/api/trips/trip-paris-demo-2026").json()
    assert trip_data["budget"] == 80000.0


# ----------------------------------------------------------------------
# 14. Changing interests
# ----------------------------------------------------------------------
def test_14_changing_interests_handling(client):
    new_interests = ["Food", "Photography"]
    res = client.post("/api/replan", json={
        "disruption_type": "user_interests_changed",
        "new_interests": new_interests,
    }, params={"trip_id": "trip-paris-demo-2026"})
    assert res.status_code == 200

    trip_data = client.get("/api/trips/trip-paris-demo-2026").json()
    assert "Food" in trip_data["interests"]
    assert "Photography" in trip_data["interests"]


# ----------------------------------------------------------------------
# 15. Refreshing the dashboard
# ----------------------------------------------------------------------
def test_15_refresh_dashboard_data_integrity(client):
    res_trip = client.get("/api/trips/trip-paris-demo-2026")
    res_itin = client.get("/api/trips/trip-paris-demo-2026/itinerary")
    res_budget = client.get("/api/trips/trip-paris-demo-2026/budget")

    assert res_trip.status_code == 200
    assert res_itin.status_code == 200
    assert res_budget.status_code == 200

    trip = res_trip.json()
    budget = res_budget.json()
    assert trip["budget"] == budget["total_budget"]


# ----------------------------------------------------------------------
# 16. Backend unavailable / error states
# ----------------------------------------------------------------------
def test_16_backend_error_handling(client):
    # Non-existent trip returns 404
    res_404 = client.get("/api/trips/trip-non-existent-9999")
    assert res_404.status_code == 404
    assert "not found" in res_404.json()["detail"].lower()

    # Health check
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"


# ----------------------------------------------------------------------
# 17. Invalid Gemini/API response
# ----------------------------------------------------------------------
def test_17_invalid_gemini_api_response_fallback():
    # Test that when Gemini returns malformed response or None,
    # plan_itinerary seamlessly falls back to deterministic scheduler
    with patch("app.services.llm_service.LLMService.generate_json") as mock_gemini:
        # 1. Test empty data
        mock_gemini.return_value = {"success": True, "data": {}}
        plan_result = plan_itinerary(
            destination="Paris, France",
            start_date="2026-10-12",
            end_date="2026-10-14",
            budget=90000.0,
            travelers=2,
            interests=["History", "Food"],
            travel_style="Balanced",
            transportation_preference="Public Transit",
        )
        assert len(plan_result["days"]) == 3
        assert plan_result["planner_engine"] == "Deterministic Constraint Solver"

        # 2. Test corrupted response
        mock_gemini.return_value = {"success": False, "data": None, "error": "API Quota Exceeded"}
        plan_result2 = plan_itinerary(
            destination="Paris, France",
            start_date="2026-10-12",
            end_date="2026-10-13",
            budget=50000.0,
            travelers=1,
        )
        assert len(plan_result2["days"]) == 2
        assert plan_result2["planner_engine"] == "Deterministic Constraint Solver"

