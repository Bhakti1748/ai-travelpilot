from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.db_models import ActivityModel
from app.models.schemas import ActivityResponse

router = APIRouter(prefix="/activities", tags=["Activities"])


@router.get("", response_model=List[ActivityResponse])
def list_activities(
    destination: Optional[str] = Query(None, description="Filter by destination (e.g. Paris)"),
    category: Optional[str] = Query(None, description="Filter by category (e.g. Food, History)"),
    db: Session = Depends(get_db),
):
    """Retrieve catalog of available activities and attractions."""
    query = db.query(ActivityModel)
    if destination:
        query = query.filter(ActivityModel.destination.ilike(f"%{destination}%"))
    if category:
        query = query.filter(ActivityModel.category.ilike(f"%{category}%"))

    activities = query.all()
    return [ActivityResponse.model_validate(a) for a in activities]


@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity(activity_id: str, db: Session = Depends(get_db)):
    """Retrieve details of a single activity by its ID."""
    act = db.query(ActivityModel).filter(ActivityModel.id == activity_id).first()
    if not act:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with ID '{activity_id}' not found.",
        )
    return ActivityResponse.model_validate(act)
