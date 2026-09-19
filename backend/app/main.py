"""
TravelPilot Backend - FastAPI Application
Provides RESTful APIs for trips, itineraries, catalog activities, budgets,
real-time disruption simulation, and AI co-pilot chat.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.activities import router as activities_router
from app.api.assistant import router as assistant_router
from app.api.budget import router as budget_router
from app.api.disruptions import router as disruptions_router
from app.api.itinerary import router as itinerary_router
from app.api.trips import router as trips_router
from app.database.session import Base, SessionLocal, engine
from app.services.travel_service import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize SQLite Database Schema
    Base.metadata.create_all(bind=engine)

    # 2. Seed Initial Demonstration Trip & Activities
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

    yield


app = FastAPI(
    title="TravelPilot API",
    description="Autonomous AI Travel Planning and Real-time Disruption Management API.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration for React/Vite Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
            "path": str(request.url),
        },
    )


# Health Check Endpoints
@app.get("/api/health", tags=["Health"])
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "TravelPilot API",
        "version": "1.0.0",
        "database": "SQLite (Connected)",
        "demo_trip_id": "trip-paris-demo-2026",
    }


# Include Routers under /api
app.include_router(trips_router, prefix="/api")
app.include_router(itinerary_router, prefix="/api")
app.include_router(activities_router, prefix="/api")
app.include_router(budget_router, prefix="/api")
app.include_router(disruptions_router, prefix="/api")
app.include_router(assistant_router, prefix="/api")

# Top-level and Global Convenience Endpoints for Disruptions & Assistant
from app.agents.disruption_manager import default_disruption_manager
from app.agents.travel_assistant import default_travel_assistant
from app.database.session import get_db
from app.models.db_models import TripModel
from app.models.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatResponse,
    DisruptionSimulateRequest,
    DisruptionSimulationResponse,
    ItineraryItemResponse,
    ReplanRequest,
    ReplanResponse,
)
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session


def _resolve_trip_id(trip_id: str | None, db: Session) -> str:
    if trip_id:
        return trip_id
    trip = db.query(TripModel).first()
    return trip.id if trip else "trip-paris-demo-2026"


@app.post("/api/disruptions/simulate", response_model=DisruptionSimulationResponse, tags=["Disruptions"])
@app.post("/disruptions/simulate", response_model=DisruptionSimulationResponse, tags=["Disruptions"])
def global_simulate_disruption(
    payload: DisruptionSimulateRequest,
    trip_id: str | None = None,
    db: Session = Depends(get_db),
):
    resolved_id = _resolve_trip_id(trip_id, db)
    trip = db.query(TripModel).filter(TripModel.id == resolved_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail=f"Trip '{resolved_id}' not found.")
    sim_result = default_disruption_manager.simulate_disruption(
        trip_id=resolved_id,
        disruption_type=payload.disruption_type,
        activity_id=payload.activity_id,
        title=payload.title,
        time=payload.time,
        delay_minutes=payload.delay_minutes or 0,
        cost_delta=payload.cost_delta or 0.0,
        new_budget=payload.new_budget,
        new_interests=payload.new_interests,
        db=db,
    )
    return DisruptionSimulationResponse(**sim_result)


@app.post("/api/replan", response_model=ReplanResponse, tags=["Disruptions"])
@app.post("/replan", response_model=ReplanResponse, tags=["Disruptions"])
def global_replan(
    payload: ReplanRequest | None = None,
    trip_id: str | None = None,
    db: Session = Depends(get_db),
):
    resolved_id = _resolve_trip_id(trip_id, db)
    trip = db.query(TripModel).filter(TripModel.id == resolved_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail=f"Trip '{resolved_id}' not found.")
    p = payload or ReplanRequest()
    replan_result = default_disruption_manager.replan_and_apply(
        trip_id=resolved_id,
        disruption_type=p.disruption_type or "activity_cancelled",
        activity_id=p.activity_id,
        title=p.title,
        time=p.time,
        delay_minutes=p.delay_minutes or 0,
        cost_delta=p.cost_delta or 0.0,
        new_budget=p.new_budget,
        new_interests=p.new_interests,
        db=db,
    )
    return ReplanResponse(
        trip_id=replan_result["trip_id"],
        status=replan_result["status"],
        disruptions_addressed=replan_result["disruptions_addressed"],
        summary_of_changes=replan_result["summary_of_changes"],
        affected_itinerary_count=replan_result["affected_itinerary_count"],
        updated_spending=replan_result["updated_spending"],
        budget_impact=replan_result.get("budget_impact"),
        travel_impact=replan_result.get("travel_impact"),
        changes_made=replan_result.get("changes_made", []),
        recommended_alternative=replan_result.get("recommended_alternative"),
        updated_itinerary=[
            ItineraryItemResponse.model_validate(item)
            for item in replan_result["updated_itinerary"]
        ],
    )


@app.post("/assistant/chat", response_model=ChatResponse, tags=["AI Assistant"])
def root_chat(payload: ChatMessageRequest, db: Session = Depends(get_db)):
    chat_result = default_travel_assistant.chat(
        message=payload.message,
        trip_id=payload.trip_id,
        db=db,
    )
    return ChatResponse(
        status=chat_result["status"],
        intent=chat_result.get("intent"),
        action_type=chat_result.get("action_type"),
        user_message=ChatMessageResponse(**chat_result["user_message"]),
        ai_response=ChatMessageResponse(**chat_result["ai_response"]),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
