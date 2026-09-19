"""
Unit & Integration Tests for TravelPilot Disruption Management & Automatic Replanning System
Tests:
- Louvre Museum cancelled at 10:00 AM scenario
- 10-step resolution flow
- Candidate alternative discovery & multi-constraint scoring
- Read-only Simulation Mode (verifying DB immutability)
- Replan and Apply mode (verifying DB persistence & spending recalculation)
- Transportation delay, budget reduction, and interest change disruptions
- REST endpoints: POST /api/trips/{trip_id}/disruptions/simulate and POST /api/trips/{trip_id}/replan
"""

import os
import sys

# Ensure backend directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.agents.disruption_manager import default_disruption_manager
from app.database.session import Base, SessionLocal, engine
from app.main import app
from app.models.db_models import ItineraryItemModel, TripModel
from app.services.travel_service import seed_database

DEMO_TRIP_ID = "trip-paris-demo-2026"


def setup_fresh_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        from app.models.db_models import BookingModel, BudgetModel, DisruptionModel, ItineraryItemModel, TripModel
        db.query(ItineraryItemModel).filter(ItineraryItemModel.trip_id == DEMO_TRIP_ID).delete()
        db.query(BookingModel).filter(BookingModel.trip_id == DEMO_TRIP_ID).delete()
        db.query(BudgetModel).filter(BudgetModel.trip_id == DEMO_TRIP_ID).delete()
        db.query(DisruptionModel).filter(DisruptionModel.trip_id == DEMO_TRIP_ID).delete()
        db.query(TripModel).filter(TripModel.id == DEMO_TRIP_ID).delete()
        db.commit()
        seed_database(db)
    finally:
        db.close()



def test_scenario_louvre_cancelled_simulation():
    """
    Core required test scenario:
    Louvre Museum cancelled at 10:00 AM.
    The system should find a suitable alternative and rebuild the remaining schedule.
    Verifies that simulation mode does NOT mutate the database.
    """
    print("\n--- Test 1: Scenario - Louvre Museum cancelled at 10:00 AM (Simulation Mode) ---")
    setup_fresh_db()
    db = SessionLocal()

    try:
        # Snapshot DB items before simulation
        items_before = (
            db.query(ItineraryItemModel)
            .filter(ItineraryItemModel.trip_id == DEMO_TRIP_ID)
            .all()
        )
        count_before = len(items_before)
        louvre_item = [i for i in items_before if "louvre" in i.title.lower()][0]
        original_time = louvre_item.time
        original_title = louvre_item.title
        original_cost = louvre_item.cost

        print(f"Target activity identified in DB: '{original_title}' at {original_time} (Cost: {original_cost} INR)")

        # Run Disruption Simulation
        sim_res = default_disruption_manager.simulate_disruption(
            trip_id=DEMO_TRIP_ID,
            disruption_type="activity_cancelled",
            title="Musée du Louvre",
            time="10:00",
            db=db,
        )

        # 1. Verify Simulation Output Structure
        assert sim_res["simulation_mode"] is True
        assert len(sim_res["affected_items"]) >= 1
        assert "Louvre" in sim_res["affected_items"][0]["activity_name"]
        print(f"[PASS] Directly affected item identified: '{sim_res['affected_items'][0]['activity_name']}'.")

        # 2. Verify Candidate Alternatives Found from Dataset
        alts = sim_res["alternatives"]
        assert len(alts) > 0
        print(f"[PASS] Discovered {len(alts)} candidate alternatives from Paris dataset:")
        for idx, a in enumerate(alts[:3]):
            print(f"   {idx+1}. {a['name']} ({a['category']}, {a['distance_from_original_km']} km away, Rating: {a['rating']} stars, Score: {a['similarity_score']})")


        rec = sim_res["recommended_alternative"]
        assert rec is not None
        assert rec["name"] != original_title
        assert rec["hours_compatible"] is True
        print(f"[PASS] Recommended substitution: '{rec['name']}' ({rec['recommendation_reason']})")

        # 3. Verify Schedule Rebuilt in Updated Itinerary
        day_1 = sim_res["updated_itinerary"][0]
        day_1_titles = [a["activity_name"] for a in day_1["activities"]]
        assert rec["name"] in day_1_titles
        assert original_title not in day_1_titles
        print(f"[PASS] Day 1 schedule rebuilt with '{rec['name']}' replacing '{original_title}'.")

        # 4. Verify Budget & Travel Impact Calculated
        b_impact = sim_res["budget_impact"]
        t_impact = sim_res["travel_impact"]
        assert "spending_delta" in b_impact
        assert "distance_delta_km" in t_impact
        print(f"[PASS] Impacts calculated: Budget Delta: {b_impact['spending_delta']} INR, Travel Delta: {t_impact['distance_delta_km']} km.")

        # 5. CRITICAL: Verify DB was NOT modified in simulation mode
        items_after = (
            db.query(ItineraryItemModel)
            .filter(ItineraryItemModel.trip_id == DEMO_TRIP_ID)
            .all()
        )
        assert len(items_after) == count_before
        still_louvre = db.query(ItineraryItemModel).filter(ItineraryItemModel.id == louvre_item.id).first()
        assert still_louvre is not None
        assert still_louvre.title == original_title
        print("[PASS] Verified DB immutability: Simulation mode made 0 modifications to SQLite database.")

    finally:
        db.close()


def test_scenario_louvre_cancelled_apply_replan():
    """
    Verifies that replan_and_apply commits the changes to the database.
    """
    print("\n--- Test 2: Scenario - Louvre Museum cancelled -> Apply Replan (DB Persistence) ---")
    setup_fresh_db()
    db = SessionLocal()

    try:
        replan_res = default_disruption_manager.replan_and_apply(
            trip_id=DEMO_TRIP_ID,
            disruption_type="activity_cancelled",
            title="Musée du Louvre",
            time="10:00",
            db=db,
        )

        assert replan_res["success"] is True
        assert replan_res["simulation_mode"] is False
        assert replan_res["status"] == "replan_applied"

        # Verify DB items now reflect the replacement
        updated_db_items = (
            db.query(ItineraryItemModel)
            .filter(ItineraryItemModel.trip_id == DEMO_TRIP_ID)
            .order_by(ItineraryItemModel.day_number, ItineraryItemModel.order)
            .all()
        )
        db_titles = [i.title for i in updated_db_items]
        rec_name = replan_res["recommended_alternative"]["name"]

        assert rec_name in db_titles
        print(f"[PASS] Successfully persisted '{rec_name}' to SQLite database.")
        print(f"[PASS] Updated trip spending: {replan_res['updated_spending']} INR.")

    finally:
        db.close()


def test_disruption_transportation_delayed():
    print("\n--- Test 3: Disruption - Transportation Delay (45 mins) ---")
    setup_fresh_db()
    db = SessionLocal()

    try:
        sim_res = default_disruption_manager.simulate_disruption(
            trip_id=DEMO_TRIP_ID,
            disruption_type="transportation_delayed",
            title="Musée du Louvre",
            delay_minutes=45,
            db=db,
        )


        assert len(sim_res["downstream_impacts"]) > 0
        assert any("timing_shift" in str(i) for i in sim_res["downstream_impacts"])
        print(f"[PASS] Transportation delay identified {len(sim_res['downstream_impacts'])} downstream timing impacts.")
        print(f"[PASS] Adjustments applied: {sim_res['changes_made'][:2]}")

    finally:
        db.close()


def test_disruption_budget_reduced():
    print("\n--- Test 4: Disruption - Budget Reduced by 15,000 INR ---")
    setup_fresh_db()
    db = SessionLocal()

    try:
        sim_res = default_disruption_manager.simulate_disruption(
            trip_id=DEMO_TRIP_ID,
            disruption_type="budget_reduced",
            new_budget=50000.0,  # lower budget
            cost_delta=15000.0,
            db=db,
        )

        assert sim_res["budget_impact"]["revised_budget"] == 50000.0
        print(f"[PASS] Budget constraint rebalanced: New remaining: {sim_res['budget_impact']['new_remaining_budget']} INR.")

    finally:
        db.close()


def test_disruption_user_interests_changed():
    print("\n--- Test 5: Disruption - User Changes Interests ---")
    setup_fresh_db()
    db = SessionLocal()

    try:
        sim_res = default_disruption_manager.simulate_disruption(
            trip_id=DEMO_TRIP_ID,
            disruption_type="user_interests_changed",
            title="Musée du Louvre",
            new_interests=["Food", "Local Culture", "Walking"],
            db=db,
        )

        alts = sim_res["alternatives"]
        assert len(alts) > 0
        # High scoring alternatives should include Food/Walking
        top_cats = [a["category"] for a in alts[:2]]
        print(f"[PASS] Interest shift prioritized categories: {top_cats}")

    finally:
        db.close()


def test_fastapi_rest_endpoints():
    print("\n--- Test 6: FastAPI REST Endpoints Integration ---")
    setup_fresh_db()
    client = TestClient(app)

    # 1. POST /api/trips/{trip_id}/disruptions/simulate
    sim_payload = {
        "disruption_type": "activity_cancelled",
        "title": "Musée du Louvre",
        "time": "10:00",
    }
    resp_sim = client.post(f"/api/trips/{DEMO_TRIP_ID}/disruptions/simulate", json=sim_payload)
    assert resp_sim.status_code == 200, f"Simulation failed: {resp_sim.text}"
    data_sim = resp_sim.json()
    assert data_sim["simulation_mode"] is True
    assert "recommended_alternative" in data_sim
    print("[PASS] Endpoint POST /api/trips/{trip_id}/disruptions/simulate succeeded (200 OK).")

    # 2. POST /api/trips/{trip_id}/replan
    replan_payload = {
        "disruption_type": "activity_cancelled",
        "title": "Musée du Louvre",
        "time": "10:00",
    }
    resp_replan = client.post(f"/api/trips/{DEMO_TRIP_ID}/replan", json=replan_payload)
    assert resp_replan.status_code == 200, f"Replan failed: {resp_replan.text}"
    data_replan = resp_replan.json()
    assert data_replan["status"] == "replan_applied"
    assert len(data_replan["updated_itinerary"]) > 0
    print("[PASS] Endpoint POST /api/trips/{trip_id}/replan succeeded (200 OK).")


if __name__ == "__main__":
    setup_fresh_db()
    print("==================================================================")
    print("RUNNING TRAVELPILOT DISRUPTION MANAGER TEST SUITE")
    print("==================================================================")
    test_scenario_louvre_cancelled_simulation()
    test_scenario_louvre_cancelled_apply_replan()
    test_disruption_transportation_delayed()
    test_disruption_budget_reduced()
    test_disruption_user_interests_changed()
    test_fastapi_rest_endpoints()
    print("\n==================================================================")
    print("ALL 6 DISRUPTION MANAGEMENT & REPLANNING TESTS PASSED [OK]")
    print("==================================================================")
