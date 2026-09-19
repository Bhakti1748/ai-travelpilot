import uuid
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.db_models import ItineraryItemModel, TripModel
from app.models.schemas import (
    ItineraryDayGroup,
    ItineraryItemResponse,
    ItineraryResponse,
    ItineraryUpdateRequest,
)
from app.services.travel_service import generate_itinerary_for_trip

router = APIRouter(prefix="/trips/{trip_id}/itinerary", tags=["Itinerary"])


def build_itinerary_response(trip: TripModel, db: Session) -> ItineraryResponse:
    items = (
        db.query(ItineraryItemModel)
        .filter(ItineraryItemModel.trip_id == trip.id)
        .order_by(ItineraryItemModel.day_number, ItineraryItemModel.order, ItineraryItemModel.time)
        .all()
    )

    day_map: Dict[int, List[ItineraryItemModel]] = {}
    for item in items:
        day_map.setdefault(item.day_number, []).append(item)

    day_groups = []
    for day_num in sorted(day_map.keys()):
        day_items = day_map[day_num]
        date_str = day_items[0].date if day_items else trip.start_date
        total_cost = sum(i.cost for i in day_items)

        day_groups.append(
            ItineraryDayGroup(
                day_number=day_num,
                date=date_str,
                title=f"Day {day_num}: {trip.destination} Highlights & Experiences",
                total_cost=round(total_cost, 2),
                activities=[ItineraryItemResponse.model_validate(i) for i in day_items],
            )
        )

    return ItineraryResponse(
        trip_id=trip.id,
        destination=trip.destination,
        total_days=len(day_groups),
        total_activities=len(items),
        days=day_groups,
    )


@router.get("", response_model=ItineraryResponse)
def get_itinerary(trip_id: str, db: Session = Depends(get_db)):
    """Retrieve full day-by-day itinerary timeline for a specific trip."""
    trip = db.query(TripModel).filter(TripModel.id == trip_id).first()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID '{trip_id}' not found.",
        )
    return build_itinerary_response(trip, db)


@router.post("/generate", response_model=ItineraryResponse)
def generate_itinerary(trip_id: str, db: Session = Depends(get_db)):
    """Synthesize or regenerate a complete adaptive itinerary for the trip."""
    trip = db.query(TripModel).filter(TripModel.id == trip_id).first()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID '{trip_id}' not found.",
        )

    generate_itinerary_for_trip(trip, db)
    return build_itinerary_response(trip, db)


@router.put("", response_model=ItineraryResponse)
def update_itinerary(
    trip_id: str, payload: ItineraryUpdateRequest, db: Session = Depends(get_db)
):
    """Replace or bulk update the itinerary items for a specific trip."""
    trip = db.query(TripModel).filter(TripModel.id == trip_id).first()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID '{trip_id}' not found.",
        )

    # Delete existing items
    db.query(ItineraryItemModel).filter(ItineraryItemModel.trip_id == trip.id).delete()

    total_cost = 0.0
    for idx, item in enumerate(payload.items):
        new_item = ItineraryItemModel(
            id=f"item-{uuid.uuid4().hex[:8]}",
            trip_id=trip.id,
            day_number=item.day_number,
            date=item.date,
            time=item.time,
            title=item.title,
            category=item.category,
            duration=item.duration,
            location=item.location,
            cost=item.cost,
            currency=item.currency or trip.currency,
            transportation=item.transportation,
            status=item.status,
            notes=item.notes,
            order=idx + 1,
        )
        total_cost += item.cost
        db.add(new_item)

    trip.spending = min(trip.budget, total_cost)
    db.commit()

    return build_itinerary_response(trip, db)
