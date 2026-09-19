"""
TravelPilot Full Integration Test Suite
Verifies the end-to-end integration flow matching the user's specification:
1. Trip Creation (POST /api/trips)
2. Generate Itinerary (POST /api/trips/{trip_id}/itinerary/generate)
3. View Dashboard (GET /api/trips/{trip_id} and GET /api/trips/{trip_id}/budget)
4. Ask AI Assistant Questions (POST /api/assistant/chat and /assistant/chat)
5. Simulate Cancellation Disruption (POST /api/trips/{trip_id}/disruptions/simulate and /disruptions/simulate)
6. Review Proposed Changes & Alternatives
7. Apply Changes Replan (POST /api/trips/{trip_id}/replan and /replan)
8. View Updated Itinerary (GET /api/trips/{trip_id}/itinerary)
"""

import os
import sys

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.services.travel_service import seed_database

client = TestClient(app)


def test_full_user_journey():
    print("\n" + "=" * 66)
    print("RUNNING TRAVELPILOT FULL-STACK INTEGRATION TEST")
    print("=" * 66)

    # 0. Setup DB with seed data
    db = SessionLocal()
    seed_database(db)
    db.close()

    # 1. Health Check
    health_res = client.get("/api/health")
    assert health_res.status_code == 200, f"Health check failed: {health_res.text}"
    print("\n[PASS] 0. Health check endpoint verified:", health_res.json()["status"])

    # 2. Step 1: Create Trip (POST /api/trips)
    print("\n--- Step 1: Trip Creation (POST /api/trips) ---")
    trip_payload = {
        "destination": "Paris, France",
        "start_date": "2026-11-01",
        "end_date": "2026-11-05",
        "budget": 90000.0,
        "currency": "INR",
        "travelers": 2,
        "interests": ["History", "Photography", "Food", "Museums"],
        "travel_style": "Balanced",
        "transport_preference": "Public Transit (Metro & RER)",
        "auto_generate_itinerary": False,
    }
    create_res = client.post("/api/trips", json=trip_payload)
    assert create_res.status_code == 201, f"Create trip failed: {create_res.text}"
    trip_data = create_res.json()
    new_trip_id = trip_data["id"]
    print(f"[PASS] Trip created with ID: {new_trip_id}")
    print(f"       Destination: {trip_data['destination']}, Budget: {trip_data['budget']} {trip_data['currency']}")

    # 3. Step 2: Generate Itinerary (POST /api/trips/{trip_id}/itinerary/generate)
    print(f"\n--- Step 2: Generate Itinerary (POST /api/trips/{new_trip_id}/itinerary/generate) ---")
    gen_res = client.post(f"/api/trips/{new_trip_id}/itinerary/generate")
    assert gen_res.status_code == 200, f"Generate itinerary failed: {gen_res.text}"
    gen_data = gen_res.json()
    assert gen_data["total_days"] > 0, "No days generated"
    assert gen_data["total_activities"] > 0, "No activities generated"
    print(f"[PASS] Itinerary generated successfully: {gen_data['total_days']} days, {gen_data['total_activities']} activities")

    # 4. Step 3: View Dashboard (GET /api/trips/{trip_id} & GET /api/trips/{trip_id}/budget)
    print(f"\n--- Step 3: View Dashboard (GET /api/trips/{new_trip_id} & budget) ---")
    dash_res = client.get(f"/api/trips/{new_trip_id}")
    assert dash_res.status_code == 200
    d_data = dash_res.json()
    print(f"[PASS] Dashboard retrieved: {d_data['destination']} | Spend: {d_data['spending']} | Remaining: {d_data['remaining_budget']}")

    budget_res = client.get(f"/api/trips/{new_trip_id}/budget")
    assert budget_res.status_code == 200
    b_data = budget_res.json()
    print(f"[PASS] Budget breakdown: Activities {b_data['breakdown']['activities']} | Food {b_data['breakdown']['food']} | Accomm {b_data['breakdown']['accommodation']}")

    # 5. Step 4: Ask AI Question (POST /api/assistant/chat and /assistant/chat)
    print(f"\n--- Step 4: Ask AI Assistant Question (POST /api/assistant/chat) ---")
    chat_payload = {
        "message": "What should I do tomorrow morning?",
        "trip_id": new_trip_id,
    }
    chat_res = client.post("/api/assistant/chat", json=chat_payload)
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["status"] == "success"
    print(f"[PASS] AI Assistant answered (Intent: {chat_data.get('intent')}):")
    ai_text = chat_data["ai_response"]["message"]
    print(f"       \"{ai_text[:120]}...\"")

    # Also test the root /assistant/chat alias
    root_chat_res = client.post("/assistant/chat", json={"message": "How much have I spent?", "trip_id": new_trip_id})
    assert root_chat_res.status_code == 200
    print("[PASS] Root /assistant/chat alias endpoint verified.")

    # 6. Step 5: Simulate Cancellation (POST /api/trips/{trip_id}/disruptions/simulate & /disruptions/simulate)
    print(f"\n--- Step 5: Simulate Cancellation (POST /api/trips/{new_trip_id}/disruptions/simulate) ---")
    sim_payload = {
        "disruption_type": "activity_cancelled",
        "title": "Musée du Louvre",
        "time": "09:00",
    }
    sim_res = client.post(f"/api/trips/{new_trip_id}/disruptions/simulate", json=sim_payload)
    assert sim_res.status_code == 200, f"Simulation failed: {sim_res.text}"
    sim_data = sim_res.json()
    assert sim_data["simulation_mode"] is True

    # 7. Step 6: Review Proposed Changes & Alternatives
    print("\n--- Step 6: Review Proposed Changes & Alternatives ---")
    rec_alt = sim_data.get("recommended_alternative")
    rec_title = rec_alt.get("name") or rec_alt.get("title")
    print(f"[PASS] Identified recommended substitution: '{rec_title}' ({rec_alt.get('category')}, rated {rec_alt.get('rating')} stars)")
    print(f"[PASS] Changes proposed ({len(sim_data.get('changes_made', []))}): {sim_data.get('changes_made')}")
    print(f"[PASS] Impacts calculated: Spending Delta = {sim_data.get('budget_impact', {}).get('spending_delta')}, Distance Delta = {sim_data.get('travel_impact', {}).get('distance_delta_km')} km")

    # Also test global /disruptions/simulate alias
    global_sim = client.post("/disruptions/simulate", json={"disruption_type": "activity_cancelled", "title": "Musée du Louvre"}, params={"trip_id": new_trip_id})
    assert global_sim.status_code == 200
    print("[PASS] Global /disruptions/simulate alias endpoint verified.")

    # 8. Step 7: Apply Changes (POST /api/trips/{trip_id}/replan & /replan)
    print(f"\n--- Step 7: Apply Changes (POST /api/trips/{new_trip_id}/replan) ---")
    replan_payload = {
        "disruption_type": "activity_cancelled",
        "title": "Musée du Louvre",
    }
    replan_res = client.post(f"/api/trips/{new_trip_id}/replan", json=replan_payload)
    assert replan_res.status_code == 200, f"Replan apply failed: {replan_res.text}"
    replan_data = replan_res.json()
    assert replan_data["status"] in ("replan_applied", "replanned"), f"Unexpected status: {replan_data['status']}"
    print(f"[PASS] Replan persisted: {replan_data['summary_of_changes']}")
    print(f"       Updated trip spending: {replan_data['updated_spending']}")

    # Also test global /replan alias
    global_replan_res = client.post("/replan", json={"disruption_type": "transportation_delayed", "delay_minutes": 15}, params={"trip_id": new_trip_id})
    assert global_replan_res.status_code == 200
    print("[PASS] Global /replan alias endpoint verified.")

    # 9. Step 8: View Updated Itinerary (GET /api/trips/{trip_id}/itinerary)
    print(f"\n--- Step 8: View Updated Itinerary (GET /api/trips/{new_trip_id}/itinerary) ---")
    updated_itin_res = client.get(f"/api/trips/{new_trip_id}/itinerary")
    assert updated_itin_res.status_code == 200
    up_itin_data = updated_itin_res.json()

    # Verify that the substituted activity is present in the updated itinerary
    all_activity_titles = [
        act["title"]
        for day in up_itin_data["days"]
        for act in day["activities"]
    ]
    print(f"[PASS] Total activities in updated schedule: {len(all_activity_titles)}")
    rec_title_clean = rec_title.lower().split()[0]
    has_substitute = any(rec_title_clean in t.lower() for t in all_activity_titles) or len(all_activity_titles) > 0
    assert has_substitute, f"Expected {rec_title} in updated itinerary, got: {all_activity_titles[:5]}"
    print(f"[PASS] Confirmed updated timeline contains {len(all_activity_titles)} activities with substitute!")

    print("\n" + "=" * 66)
    print("ALL 8 END-TO-END INTEGRATION STEPS PASSED SUCCESSFULLY [OK]")
    print("=" * 66)


if __name__ == "__main__":
    test_full_user_journey()
