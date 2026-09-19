from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.db_models import BudgetModel, TripModel
from app.models.schemas import BudgetBreakdown, BudgetResponse

router = APIRouter(prefix="/trips/{trip_id}/budget", tags=["Budget"])


@router.get("", response_model=BudgetResponse)
def get_trip_budget(trip_id: str, db: Session = Depends(get_db)):
    """Retrieve financial status and category breakdown for a trip."""
    trip = db.query(TripModel).filter(TripModel.id == trip_id).first()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID '{trip_id}' not found.",
        )

    budget_rec = (
        db.query(BudgetModel).filter(BudgetModel.trip_id == trip.id).first()
    )

    total = trip.budget
    spent = trip.spending
    remaining = max(0.0, total - spent)
    utilization = round((spent / total) * 100, 1) if total > 0 else 0.0

    if utilization > 90:
        status_flag = "critical"
    elif utilization > 75:
        status_flag = "warning"
    else:
        status_flag = "healthy"

    if budget_rec:
        breakdown = BudgetBreakdown(
            accommodation=budget_rec.accommodation,
            transportation=budget_rec.transportation,
            activities=budget_rec.activities,
            food=budget_rec.food,
            miscellaneous=budget_rec.miscellaneous,
        )
    else:
        breakdown = BudgetBreakdown(
            accommodation=round(total * 0.35, 2),
            transportation=round(total * 0.20, 2),
            activities=round(total * 0.20, 2),
            food=round(total * 0.20, 2),
            miscellaneous=round(total * 0.05, 2),
        )

    return BudgetResponse(
        trip_id=trip.id,
        destination=trip.destination,
        total_budget=total,
        currency=trip.currency,
        estimated_spending=spent,
        remaining_budget=remaining,
        percent_utilized=utilization,
        breakdown=breakdown,
        status=status_flag,
    )
