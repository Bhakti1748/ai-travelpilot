"""
Unit & Integration Tests for TravelPilot Conversational AI Assistant
Verifies the agent loop across all target questions:
1. "What should I do tomorrow morning?"
2. "Can I fit this activity into today's schedule?"
3. "Which activities are close to my hotel?"
4. "What happens if my museum booking is cancelled?"
5. "Apply it." (Confirmation flow with 'Why I changed this' reasoning)
6. "How much have I spent?"
7. "Can I reduce my budget to 70000 INR?"
8. "What activities match my photography interest?"
9. FastAPI REST integration at POST /api/assistant/chat
"""

import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.agents.travel_assistant import default_travel_assistant
from app.database.session import Base, SessionLocal, engine
from app.main import app
from app.models.db_models import (
    BookingModel,
    BudgetModel,
    ChatMessageModel,
    DisruptionModel,
    ItineraryItemModel,
    TripModel,
)
from app.services.travel_service import seed_database

DEMO_TRIP_ID = "trip-paris-demo-2026"


def setup_fresh_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(ItineraryItemModel).filter(ItineraryItemModel.trip_id == DEMO_TRIP_ID).delete()
        db.query(BookingModel).filter(BookingModel.trip_id == DEMO_TRIP_ID).delete()
        db.query(BudgetModel).filter(BudgetModel.trip_id == DEMO_TRIP_ID).delete()
        db.query(DisruptionModel).filter(DisruptionModel.trip_id == DEMO_TRIP_ID).delete()
        db.query(ChatMessageModel).filter(ChatMessageModel.trip_id == DEMO_TRIP_ID).delete()
        db.query(TripModel).filter(TripModel.id == DEMO_TRIP_ID).delete()
        db.commit()
        seed_database(db)
    finally:
        db.close()


def test_question_tomorrow_morning():
    print("\n--- Test 1: Question - 'What should I do tomorrow morning?' ---")
    setup_fresh_db()
    res = default_travel_assistant.chat(
        message="What should I do tomorrow morning?",
        trip_id=DEMO_TRIP_ID,
    )
    assert res["status"] == "success"
    assert res["intent"] == "itinerary_query"
    ai_msg = res["ai_response"]["message"]
    assert "schedule for Day 2" in ai_msg or "Day 2" in ai_msg
    print(f"[PASS] Itinerary retrieved:\n{ai_msg[:160]}...")


def test_question_fit_activity():
    print("\n--- Test 2: Question - 'Can I fit this activity into today's schedule?' ---")
    setup_fresh_db()
    res = default_travel_assistant.chat(
        message="Can I fit Musée d'Orsay into today's schedule?",
        trip_id=DEMO_TRIP_ID,
    )
    assert res["status"] == "success"
    assert res["intent"] == "schedule_feasibility"
    ai_msg = res["ai_response"]["message"]
    assert "Operating Hours" in ai_msg
    assert "Estimated Duration" in ai_msg
    assert "Transit Buffer" in ai_msg
    print(f"[PASS] Schedule feasibility answered:\n{ai_msg[:200]}...")


def test_question_close_to_hotel():
    print("\n--- Test 3: Question - 'Which activities are close to my hotel?' ---")
    setup_fresh_db()
    res = default_travel_assistant.chat(
        message="Which activities are close to my hotel?",
        trip_id=DEMO_TRIP_ID,
    )
    assert res["status"] == "success"
    assert res["intent"] == "proximity_query"
    ai_msg = res["ai_response"]["message"]
    assert "hotel" in ai_msg.lower()
    assert "walking" in ai_msg.lower()
    print(f"[PASS] Nearby activities retrieved:\n{ai_msg[:220]}...")


def test_question_disruption_and_confirmation_flow():
    print("\n--- Test 4 & 5: Disruption Simulation -> 'Apply it' Confirmation Flow ---")
    setup_fresh_db()

    # Turn 1: User asks what if Louvre is cancelled
    res_disrupt = default_travel_assistant.chat(
        message="What happens if the Louvre is cancelled?",
        trip_id=DEMO_TRIP_ID,
    )
    assert res_disrupt["status"] == "success"
    assert res_disrupt["intent"] == "disruption_simulation"
    assert res_disrupt["action_type"] == "proposal"

    ai_msg_1 = res_disrupt["ai_response"]["message"]
    assert "Disruption Impact" in ai_msg_1
    assert "Recommended Alternative" in ai_msg_1
    assert "apply these changes" in ai_msg_1.lower()
    assert "Apply it." in res_disrupt["ai_response"]["suggestions"]
    print(f"[PASS] Disruption simulated and proposal presented with alternatives.")

    # Turn 2: User confirms "Apply it."
    res_confirm = default_travel_assistant.chat(
        message="Apply it.",
        trip_id=DEMO_TRIP_ID,
    )
    assert res_confirm["status"] == "success"
    assert res_confirm["intent"] == "confirm_apply"
    assert res_confirm["action_type"] == "applied"

    ai_msg_2 = res_confirm["ai_response"]["message"]
    assert "Why I changed this" in ai_msg_2
    assert "cancelled" in ai_msg_2.lower()
    assert "closer to your next activity" in ai_msg_2.lower()
    assert "within budget" in ai_msg_2.lower()
    print(f"[PASS] Confirmed and applied with concise explanation:\n{ai_msg_2[:320]}...")


def test_question_how_much_spent():
    print("\n--- Test 6: Question - 'How much have I spent?' ---")
    setup_fresh_db()
    res = default_travel_assistant.chat(
        message="How much have I spent?",
        trip_id=DEMO_TRIP_ID,
    )
    assert res["status"] == "success"
    assert res["intent"] == "budget_query"
    ai_msg = res["ai_response"]["message"]
    assert "Total Budget" in ai_msg
    assert "Total Committed Spending" in ai_msg
    assert "Category Allocations" in ai_msg
    print(f"[PASS] Budget audit answered:\n{ai_msg[:200]}...")


def test_question_reduce_budget():
    print("\n--- Test 7: Question - 'Can I reduce my budget to 70000 INR?' ---")
    setup_fresh_db()
    res = default_travel_assistant.chat(
        message="Can I reduce my budget to 70000 INR?",
        trip_id=DEMO_TRIP_ID,
    )
    assert res["status"] == "success"
    assert res["intent"] == "budget_adjustment"
    ai_msg = res["ai_response"]["message"]
    assert "70,000" in ai_msg or "70000" in ai_msg
    print(f"[PASS] Budget reduction evaluated:\n{ai_msg[:200]}...")


def test_question_photography_interest():
    print("\n--- Test 8: Question - 'What activities match my photography interest?' ---")
    setup_fresh_db()
    res = default_travel_assistant.chat(
        message="What activities match my photography interest?",
        trip_id=DEMO_TRIP_ID,
    )
    assert res["status"] == "success"
    assert res["intent"] == "interest_query"
    ai_msg = res["ai_response"]["message"]
    assert "Photography" in ai_msg
    print(f"[PASS] Photography activities matched:\n{ai_msg[:200]}...")


def test_fastapi_assistant_chat_endpoint():
    print("\n--- Test 9: FastAPI REST Endpoint POST /api/assistant/chat ---")
    setup_fresh_db()
    client = TestClient(app)

    payload = {
        "message": "What should I do tomorrow morning?",
        "trip_id": DEMO_TRIP_ID,
    }
    resp = client.post("/api/assistant/chat", json=payload)
    assert resp.status_code == 200, f"Chat failed: {resp.text}"
    data = resp.json()
    assert data["status"] == "success"
    assert "user_message" in data
    assert "ai_response" in data
    assert len(data["ai_response"]["message"]) > 20
    assert len(data["ai_response"]["suggestions"]) > 0
    print("[PASS] Endpoint POST /api/assistant/chat succeeded (200 OK) with rich structured response.")


if __name__ == "__main__":
    setup_fresh_db()
    print("==================================================================")
    print("RUNNING TRAVELPILOT CONVERSATIONAL AI ASSISTANT TEST SUITE")
    print("==================================================================")
    test_question_tomorrow_morning()
    test_question_fit_activity()
    test_question_close_to_hotel()
    test_question_disruption_and_confirmation_flow()
    test_question_how_much_spent()
    test_question_reduce_budget()
    test_question_photography_interest()
    test_fastapi_assistant_chat_endpoint()
    print("\n==================================================================")
    print("ALL 9 CONVERSATIONAL AI ASSISTANT TESTS PASSED [OK]")
    print("==================================================================")
