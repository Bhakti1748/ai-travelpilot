import datetime
import json
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.db_models import BudgetModel, DisruptionModel, ItineraryItemModel, TripModel
from app.models.schemas import TripCreate, TripResponse, TripUpdate
from app.services.travel_service import (
    format_interests,
    generate_itinerary_for_trip,
    parse_interests,
)

from app.services.currency_service import (
    get_currency_for_destination,
)

router = APIRouter(prefix="/trips", tags=["Trips"])


def map_trip_to_response(trip: TripModel, db: Session) -> TripResponse:
    # Calculate days
    try:
        s = datetime.date.fromisoformat(trip.start_date)
        e = datetime.date.fromisoformat(trip.end_date)
        days = max(1, (e - s).days + 1)
    except Exception:
        days = 1

    alerts_count = (
        db.query(DisruptionModel)
        .filter(DisruptionModel.trip_id == trip.id, DisruptionModel.resolved == False)
        .count()
    )

    items_count = (
        db.query(ItineraryItemModel)
        .filter(ItineraryItemModel.trip_id == trip.id)
        .count()
    )

    remaining = max(0.0, trip.budget - trip.spending)

    return TripResponse(
        id=trip.id,
        destination=trip.destination,
        start_date=trip.start_date,
        end_date=trip.end_date,
        budget=trip.budget,
        currency=trip.currency,
        spending=trip.spending,
        remaining_budget=remaining,
        travelers=trip.travelers,
        interests=parse_interests(trip.interests),
        travel_style=trip.travel_style,
        transport_preference=trip.transport_preference,
        status=trip.status,
        total_days=days,
        active_alerts_count=alerts_count,
        itinerary_preview_count=items_count,
    )


@router.post("", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripCreate, db: Session = Depends(get_db)):
    """Create a new trip and optionally synthesize an initial adaptive itinerary."""

    trip_id = f"trip-{uuid.uuid4().hex[:8]}"

    # ---------------------------------------------------------
    # Automatically determine local currency from destination
    # ---------------------------------------------------------
    destination_currency = get_currency_for_destination(
        payload.destination
    )

    currency_code = destination_currency["code"]

    new_trip = TripModel(
        id=trip_id,
        destination=payload.destination,
        start_date=payload.start_date,
        end_date=payload.end_date,
        budget=payload.budget,
        currency=currency_code,
        spending=0.0,
        travelers=payload.travelers,
        interests=format_interests(payload.interests),
        travel_style=payload.travel_style,
        transport_preference=payload.transport_preference,
        status="active",
    )
    db.add(new_trip)

    # Initialize budget breakdown
    budget_record = BudgetModel(
        id=f"budget-{trip_id}",
        trip_id=trip_id,
        total_budget=payload.budget,
        currency=currency_code,
        estimated_spending=0.0,
        accommodation=round(payload.budget * 0.35, 2),
        transportation=round(payload.budget * 0.20, 2),
        activities=round(payload.budget * 0.20, 2),
        food=round(payload.budget * 0.20, 2),
        miscellaneous=round(payload.budget * 0.05, 2),
    )
    db.add(budget_record)
    db.commit()
    db.refresh(new_trip)

    if payload.auto_generate_itinerary:
        generate_itinerary_for_trip(new_trip, db)
        db.refresh(new_trip)

    return map_trip_to_response(new_trip, db)


@router.get("/{trip_id}", response_model=TripResponse)
def get_trip(trip_id: str, db: Session = Depends(get_db)):
    """Retrieve details for a specific trip by its ID."""
    trip = db.query(TripModel).filter(TripModel.id == trip_id).first()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID '{trip_id}' not found.",
        )
    return map_trip_to_response(trip, db)


@router.put("/{trip_id}", response_model=TripResponse)
def update_trip(trip_id: str, payload: TripUpdate, db: Session = Depends(get_db)):
    """Update fields on an existing trip."""
    trip = db.query(TripModel).filter(TripModel.id == trip_id).first()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID '{trip_id}' not found.",
        )

    if payload.destination is not None:
        trip.destination = payload.destination
    if payload.start_date is not None:
        trip.start_date = payload.start_date
    if payload.end_date is not None:
        trip.end_date = payload.end_date
    if payload.budget is not None:
        trip.budget = payload.budget
        if trip.budget_record:
            trip.budget_record.total_budget = payload.budget
    if payload.currency is not None:
        trip.currency = payload.currency
        if trip.budget_record:
            trip.budget_record.currency = payload.currency
    if payload.travelers is not None:
        trip.travelers = payload.travelers
    if payload.interests is not None:
        trip.interests = format_interests(payload.interests)
    if payload.travel_style is not None:
        trip.travel_style = payload.travel_style
    if payload.transport_preference is not None:
        trip.transport_preference = payload.transport_preference
    if payload.status is not None:
        trip.status = payload.status

    db.commit()
    db.refresh(trip)
    return map_trip_to_response(trip, db)


@router.get("", response_model=List[TripResponse])
def list_trips(db: Session = Depends(get_db)):
    """List all registered trips."""
    trips = db.query(TripModel).order_by(TripModel.created_at.desc()).all()
    return [map_trip_to_response(t, db) for t in trips]
