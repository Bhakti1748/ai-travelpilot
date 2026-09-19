"""
Itinerary Tools for TravelPilot Agent.
Includes get_current_itinerary and update_itinerary.
"""

import logging
import uuid
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from app.database.session import SessionLocal
from app.models.db_models import ItineraryItemModel, TripModel
from app.services.dataset_service import dataset_service
from app.tools.registry import default_tool_registry

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Tool 8: get_current_itinerary
# ----------------------------------------------------------------------

class GetCurrentItineraryInput(BaseModel):
    trip_id: str = Field(..., description="Unique ID of the trip (e.g. 'trip-paris-demo-2026')")
    day_number: Optional[int] = Field(None, description="Optional specific day to fetch (1-indexed). If omitted, returns all days.")


def get_current_itinerary(
    trip_id: str,
    day_number: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Retrieves the current day-by-day itinerary schedule, items, timings, and transit notes for a trip.
    """
    db = SessionLocal()
    try:
        trip = db.query(TripModel).filter(TripModel.id == trip_id).first()
        if not trip:
            return {
                "trip_id": trip_id,
                "destination": "Unknown",
                "total_items": 0,
                "days": [],
                "error": f"Trip '{trip_id}' not found.",
            }

        query = db.query(ItineraryItemModel).filter(ItineraryItemModel.trip_id == trip_id)
        if day_number is not None:
            query = query.filter(ItineraryItemModel.day_number == day_number)

        items = query.order_by(ItineraryItemModel.day_number, ItineraryItemModel.order, ItineraryItemModel.time).all()

        days_grouped: Dict[int, List[Dict[str, Any]]] = {}
        for item in items:
            days_grouped.setdefault(item.day_number, []).append({
                "id": item.id,
                "day_number": item.day_number,
                "date": item.date,
                "time": item.time,
                "title": item.title,
                "category": item.category,
                "duration": item.duration,
                "location": item.location,
                "cost": item.cost,
                "currency": item.currency,
                "transportation": item.transportation,
                "status": item.status,
                "notes": item.notes,
                "order": item.order,
            })

        days_list = []
        for d_num in sorted(days_grouped.keys()):
            d_items = days_grouped[d_num]
            days_list.append({
                "day_number": d_num,
                "date": d_items[0]["date"] if d_items else "",
                "total_items": len(d_items),
                "total_cost": sum(it["cost"] for it in d_items),
                "items": d_items,
            })

        return {
            "trip_id": trip.id,
            "destination": trip.destination,
            "start_date": trip.start_date,
            "end_date": trip.end_date,
            "travelers": trip.travelers,
            "total_items": len(items),
            "days": days_list,
        }
    finally:
        db.close()


default_tool_registry.register(
    name="get_current_itinerary",
    description="Retrieve the current planned itinerary items, times, costs, and locations for a trip.",
    parameters_schema=GetCurrentItineraryInput.model_json_schema(),
    func=get_current_itinerary,
    input_model=GetCurrentItineraryInput,
)


# ----------------------------------------------------------------------
# Tool 12: update_itinerary
# ----------------------------------------------------------------------

class UpdateItineraryInput(BaseModel):
    trip_id: str = Field(..., description="Unique ID of the trip")
    action: Literal["add", "remove", "reschedule", "replace"] = Field(
        ..., description="Action to perform: 'add' (new item), 'remove' (delete item), 'reschedule' (change time/day), or 'replace' (swap item)"
    )
    item_id: Optional[str] = Field(None, description="ID of existing itinerary item (required for remove, reschedule, replace)")
    day_number: Optional[int] = Field(None, description="Day number (1-indexed)")
    time: Optional[str] = Field(None, description="Scheduled start time in 'HH:MM' format")
    activity_id: Optional[str] = Field(None, description="Dataset activity ID to populate name, location, and cost automatically")
    title: Optional[str] = Field(None, description="Title/name of the activity")
    category: Optional[str] = Field(None, description="Category of the activity")
    duration: Optional[str] = Field(None, description="Duration string (e.g. '1h 30m')")
    location: Optional[str] = Field(None, description="Location address or landmark name")
    cost: Optional[float] = Field(None, description="Activity cost in trip currency")
    transportation: Optional[str] = Field(None, description="Mode of transit (e.g. 'Metro', 'Walking', 'Taxi')")
    notes: Optional[str] = Field(None, description="Agent notes, tips, or disruption context")


def update_itinerary(
    trip_id: str,
    action: Literal["add", "remove", "reschedule", "replace"],
    item_id: Optional[str] = None,
    day_number: Optional[int] = None,
    time: Optional[str] = None,
    activity_id: Optional[str] = None,
    title: Optional[str] = None,
    category: Optional[str] = None,
    duration: Optional[str] = None,
    location: Optional[str] = None,
    cost: Optional[float] = None,
    transportation: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Mutates the trip itinerary by adding, removing, rescheduling, or replacing items, maintaining order and integrity.
    """
    db = SessionLocal()
    try:
        trip = db.query(TripModel).filter(TripModel.id == trip_id).first()
        if not trip:
            raise ValueError(f"Trip '{trip_id}' does not exist.")

        affected_data: Optional[Dict[str, Any]] = None

        if action == "add":
            if day_number is None:
                day_number = 1
            if not time:
                time = "10:00"

            # Auto-fill from dataset if activity_id is given
            final_title = title or "New Activity"
            final_cat = category or "General"
            final_dur = duration or "1h 30m"
            final_loc = location or trip.destination
            final_cost = cost if cost is not None else 0.0

            if activity_id:
                act = dataset_service.get_activity(activity_id)
                if act:
                    final_title = title or act.get("name", final_title)
                    final_cat = category or act.get("category", final_cat)
                    final_dur = duration or f"{act.get('duration_minutes', 90)}m"
                    final_loc = location or act.get("address", final_loc)
                    final_cost = cost if cost is not None else float(act.get("estimated_cost", 0.0))

            # Determine order
            existing_count = (
                db.query(ItineraryItemModel)
                .filter(ItineraryItemModel.trip_id == trip_id, ItineraryItemModel.day_number == day_number)
                .count()
            )

            new_item = ItineraryItemModel(
                id=f"item-{uuid.uuid4().hex[:8]}",
                trip_id=trip_id,
                day_number=day_number,
                date=trip.start_date,  # default to trip start date for demo
                time=time,
                title=final_title,
                category=final_cat,
                duration=final_dur,
                location=final_loc,
                cost=final_cost,
                currency=trip.currency or "INR",
                transportation=transportation or "Metro",
                status="Confirmed",
                notes=notes or "Added by AI Co-pilot",
                order=existing_count + 1,
            )
            db.add(new_item)
            db.commit()
            db.refresh(new_item)

            affected_data = {
                "id": new_item.id,
                "title": new_item.title,
                "time": new_item.time,
                "day_number": new_item.day_number,
                "cost": new_item.cost,
            }
            msg = f"Successfully added '{new_item.title}' at {new_item.time} on Day {new_item.day_number}."

        elif action == "remove":
            if not item_id:
                raise ValueError("Parameter 'item_id' is required for action 'remove'.")
            target = db.query(ItineraryItemModel).filter(ItineraryItemModel.id == item_id, ItineraryItemModel.trip_id == trip_id).first()
            if not target:
                raise ValueError(f"Item '{item_id}' not found in trip '{trip_id}'.")

            affected_data = {"id": target.id, "title": target.title, "day_number": target.day_number}
            msg = f"Successfully removed '{target.title}' from Day {target.day_number}."
            db.delete(target)
            db.commit()

        elif action == "reschedule":
            if not item_id:
                raise ValueError("Parameter 'item_id' is required for action 'reschedule'.")
            target = db.query(ItineraryItemModel).filter(ItineraryItemModel.id == item_id, ItineraryItemModel.trip_id == trip_id).first()
            if not target:
                raise ValueError(f"Item '{item_id}' not found in trip '{trip_id}'.")

            old_time = target.time
            old_day = target.day_number
            if time:
                target.time = time
            if day_number is not None:
                target.day_number = day_number
            if notes:
                target.notes = notes
            db.commit()

            affected_data = {
                "id": target.id,
                "title": target.title,
                "old_schedule": f"Day {old_day} at {old_time}",
                "new_schedule": f"Day {target.day_number} at {target.time}",
            }
            msg = f"Rescheduled '{target.title}' from Day {old_day} at {old_time} to Day {target.day_number} at {target.time}."

        elif action == "replace":
            if not item_id:
                raise ValueError("Parameter 'item_id' is required for action 'replace'.")
            target = db.query(ItineraryItemModel).filter(ItineraryItemModel.id == item_id, ItineraryItemModel.trip_id == trip_id).first()
            if not target:
                raise ValueError(f"Item '{item_id}' not found in trip '{trip_id}'.")

            old_title = target.title

            if activity_id:
                act = dataset_service.get_activity(activity_id)
                if act:
                    target.title = title or act.get("name", target.title)
                    target.category = category or act.get("category", target.category)
                    target.duration = duration or f"{act.get('duration_minutes', 90)}m"
                    target.location = location or act.get("address", target.location)
                    if cost is not None:
                        target.cost = cost
                    else:
                        target.cost = float(act.get("estimated_cost", target.cost))
            else:
                if title:
                    target.title = title
                if category:
                    target.category = category
                if duration:
                    target.duration = duration
                if location:
                    target.location = location
                if cost is not None:
                    target.cost = cost

            if time:
                target.time = time
            if transportation:
                target.transportation = transportation
            if notes:
                target.notes = notes

            db.commit()
            db.refresh(target)

            affected_data = {
                "id": target.id,
                "previous_title": old_title,
                "new_title": target.title,
                "day_number": target.day_number,
                "time": target.time,
                "cost": target.cost,
            }
            msg = f"Replaced '{old_title}' with '{target.title}' on Day {target.day_number} at {target.time}."

        # Fetch updated items for the affected day
        active_day = day_number if day_number is not None else (affected_data.get("day_number", 1) if affected_data else 1)
        day_items = (
            db.query(ItineraryItemModel)
            .filter(ItineraryItemModel.trip_id == trip_id, ItineraryItemModel.day_number == active_day)
            .order_by(ItineraryItemModel.order, ItineraryItemModel.time)
            .all()
        )

        return {
            "success": True,
            "trip_id": trip_id,
            "action": action,
            "message": msg,
            "affected_item": affected_data,
            "updated_day_items": [
                {"id": i.id, "time": i.time, "title": i.title, "cost": i.cost, "day_number": i.day_number}
                for i in day_items
            ],
        }
    finally:
        db.close()


default_tool_registry.register(
    name="update_itinerary",
    description="Modify an itinerary by adding new activities, removing items, rescheduling timings, or replacing with alternatives.",
    parameters_schema=UpdateItineraryInput.model_json_schema(),
    func=update_itinerary,
    input_model=UpdateItineraryInput,
)
