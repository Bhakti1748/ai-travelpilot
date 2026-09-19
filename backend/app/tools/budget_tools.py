"""
Budget Tools for TravelPilot Agent.
Includes calculate_activity_cost and calculate_trip_budget.
"""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.database.session import SessionLocal
from app.models.db_models import BudgetModel, ItineraryItemModel, TripModel
from app.services.dataset_service import dataset_service
from app.tools.registry import default_tool_registry

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Tool 7: calculate_activity_cost
# ----------------------------------------------------------------------

class CalculateActivityCostInput(BaseModel):
    activity_id: Optional[str] = Field(None, description="Activity ID from the dataset (e.g. 'act-paris-001')")
    unit_cost: Optional[float] = Field(None, description="Custom unit cost per traveler if not using dataset (in INR)")
    travelers: int = Field(1, ge=1, description="Number of travelers attending the activity")
    discount_percent: float = Field(0.0, ge=0.0, le=100.0, description="Percentage discount (e.g. 10.0 for 10% student/group discount)")
    currency: str = Field("INR", description="Currency symbol/code")


class CalculateActivityCostOutput(BaseModel):
    activity_id: Optional[str]
    activity_name: str
    unit_cost: float
    travelers: int
    subtotal: float
    discount_amount: float
    total_cost: float
    currency: str
    budget_tier: str


def calculate_activity_cost(
    activity_id: Optional[str] = None,
    unit_cost: Optional[float] = None,
    travelers: int = 1,
    discount_percent: float = 0.0,
    currency: str = "INR",
) -> Dict[str, Any]:
    """
    Calculates total cost for one or multiple travelers for an activity, applying any eligible discounts.
    """
    act_name = "Custom Activity"
    base_cost = 0.0

    if activity_id:
        act = dataset_service.get_activity(activity_id)
        if act:
            act_name = act.get("name", activity_id)
            base_cost = float(act.get("estimated_cost", 0.0))
        elif unit_cost is not None:
            base_cost = float(unit_cost)
    elif unit_cost is not None:
        base_cost = float(unit_cost)

    if unit_cost is not None and activity_id and unit_cost != base_cost:
        # Caller explicitly provided override unit cost
        base_cost = float(unit_cost)

    subtotal = round(base_cost * travelers, 2)
    discount_amount = round(subtotal * (discount_percent / 100.0), 2)
    total_cost = round(subtotal - discount_amount, 2)

    # Budget tier categorization
    if total_cost == 0:
        tier = "Free"
    elif total_cost < 1500 * travelers:
        tier = "Budget"
    elif total_cost < 4000 * travelers:
        tier = "Moderate"
    else:
        tier = "Premium"

    return {
        "activity_id": activity_id,
        "activity_name": act_name,
        "unit_cost": base_cost,
        "travelers": travelers,
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "total_cost": total_cost,
        "currency": currency,
        "budget_tier": tier,
    }


default_tool_registry.register(
    name="calculate_activity_cost",
    description="Calculate individual and group costs for an activity or custom item including discount deductions.",
    parameters_schema=CalculateActivityCostInput.model_json_schema(),
    func=calculate_activity_cost,
    input_model=CalculateActivityCostInput,
)


# ----------------------------------------------------------------------
# Tool 10: calculate_trip_budget
# ----------------------------------------------------------------------

class CalculateTripBudgetInput(BaseModel):
    trip_id: str = Field(..., description="Unique trip identifier (e.g. 'trip-paris-demo-2026')")


def calculate_trip_budget(trip_id: str) -> Dict[str, Any]:
    """
    Aggregates budget allocations, calculates current commitments from itinerary and bookings, and assesses budget health.
    """
    db = SessionLocal()
    try:
        trip = db.query(TripModel).filter(TripModel.id == trip_id).first()
        if not trip:
            return {
                "trip_id": trip_id,
                "total_budget": 0.0,
                "currency": "INR",
                "total_spent": 0.0,
                "remaining_budget": 0.0,
                "percentage_spent": 0.0,
                "is_over_budget": False,
                "categories": {},
                "spending_status": "not_found",
                "recommendations": [f"Trip '{trip_id}' not found."],
            }

        # Retrieve or compute category spending
        budget_record = db.query(BudgetModel).filter(BudgetModel.trip_id == trip_id).first()
        itinerary_items = db.query(ItineraryItemModel).filter(ItineraryItemModel.trip_id == trip_id).all()

        total_budget = trip.budget if trip.budget > 0 else (budget_record.total_budget if budget_record else 150000.0)
        currency = trip.currency or "INR"

        # Tally itinerary activities
        itinerary_activity_cost = sum(item.cost for item in itinerary_items)

        if budget_record:
            categories = {
                "accommodation": float(budget_record.accommodation),
                "transportation": float(budget_record.transportation),
                "activities": float(max(budget_record.activities, itinerary_activity_cost)),
                "food": float(budget_record.food),
                "miscellaneous": float(budget_record.miscellaneous),
            }
        else:
            categories = {
                "accommodation": 45000.0,
                "transportation": 25000.0,
                "activities": float(itinerary_activity_cost),
                "food": 20000.0,
                "miscellaneous": 5000.0,
            }

        total_spent = sum(categories.values())
        remaining = round(total_budget - total_spent, 2)
        pct_spent = round((total_spent / total_budget * 100.0) if total_budget > 0 else 0.0, 1)
        is_over = total_spent > total_budget

        recs = []
        if is_over:
            status = "exceeded"
            recs.append(f"Trip is over budget by {currency} {abs(remaining):,.2f}. Consider replacing paid activities with free alternatives.")
        elif pct_spent > 85.0:
            status = "warning"
            recs.append(f"Trip has consumed {pct_spent}% of budget. Remaining cushion is {currency} {remaining:,.2f}.")
        else:
            status = "on_track"
            recs.append(f"Trip budget is healthy with {currency} {remaining:,.2f} ({100 - pct_spent:.1f}%) unallocated.")

        return {
            "trip_id": trip_id,
            "total_budget": total_budget,
            "currency": currency,
            "total_spent": total_spent,
            "remaining_budget": remaining,
            "percentage_spent": pct_spent,
            "is_over_budget": is_over,
            "categories": categories,
            "spending_status": status,
            "recommendations": recs,
        }
    finally:
        db.close()


default_tool_registry.register(
    name="calculate_trip_budget",
    description="Inspect overall trip budget, calculate current expenditure across categories, and get budget health recommendations.",
    parameters_schema=CalculateTripBudgetInput.model_json_schema(),
    func=calculate_trip_budget,
    input_model=CalculateTripBudgetInput,
)
