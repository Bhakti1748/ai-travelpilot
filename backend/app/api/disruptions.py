"""
TravelPilot API - Disruptions & Replanning Router

Provides endpoints for:
1. Simulating travel disruptions without changing the database.
2. Applying disruptions and automatically replanning the itinerary.

The actual disruption/replanning logic lives in:
    app.agents.disruption_manager
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.disruption_manager import default_disruption_manager
from app.database.session import get_db
from app.models.db_models import TripModel
from app.models.schemas import (
    DisruptionSimulateRequest,
    DisruptionSimulationResponse,
    ItineraryItemResponse,
    ReplanRequest,
    ReplanResponse,
)


router = APIRouter(
    prefix="/trips/{trip_id}",
    tags=["Disruptions"],
)


# ============================================================
# Helper Functions
# ============================================================

def _get_trip_or_404(
    trip_id: str,
    db: Session,
) -> TripModel:
    """
    Find a trip by ID.

    Raises:
        HTTPException: If the trip does not exist.
    """

    trip = (
        db.query(TripModel)
        .filter(TripModel.id == trip_id)
        .first()
    )

    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID '{trip_id}' not found.",
        )

    return trip


def _clean_optional_string(value: Optional[str]) -> Optional[str]:
    """
    Clean optional string values.

    Converts empty strings such as "" or "   "
    into None.
    """

    if value is None:
        return None

    value = value.strip()

    return value if value else None


# ============================================================
# 1. SIMULATE DISRUPTION
# ============================================================

@router.post(
    "/disruptions/simulate",
    response_model=DisruptionSimulationResponse,
    status_code=status.HTTP_200_OK,
)
def simulate_disruption(
    trip_id: str,
    payload: DisruptionSimulateRequest,
    db: Session = Depends(get_db),
):
    """
    Simulate a disruption WITHOUT modifying the database.

    Examples of supported disruptions:

    - activity_cancelled
    - activity_unavailable
    - transport_delay
    - hotel_unavailable
    - budget_reduced
    - interests_changed
    - add_activity

    The disruption manager calculates the possible impact
    on the itinerary, budget, transportation and alternatives.

    This endpoint is useful for the TravelPilot dashboard because
    the user can preview what would happen before applying changes.
    """

    # --------------------------------------------------------
    # Validate trip
    # --------------------------------------------------------

    _get_trip_or_404(
        trip_id=trip_id,
        db=db,
    )

    # --------------------------------------------------------
    # Clean optional values
    # --------------------------------------------------------

    title = _clean_optional_string(payload.title)
    activity_id = _clean_optional_string(payload.activity_id)
    disruption_time = _clean_optional_string(payload.time)

    # --------------------------------------------------------
    # Execute simulation
    # --------------------------------------------------------

    try:
        simulation_result = (
            default_disruption_manager.simulate_disruption(
                trip_id=trip_id,
                disruption_type=payload.disruption_type,
                activity_id=activity_id,
                title=title,
                time=disruption_time,
                delay_minutes=payload.delay_minutes or 0,
                cost_delta=payload.cost_delta or 0.0,
                new_budget=payload.new_budget,
                new_interests=payload.new_interests,
                db=db,
            )
        )

        # ----------------------------------------------------
        # Return structured simulation response
        # ----------------------------------------------------

        return DisruptionSimulationResponse(
            **simulation_result
        )

    except ValueError as exc:
        # Invalid disruption data
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # Unexpected server-side error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Disruption simulation failed. "
                f"Details: {str(exc)}"
            ),
        ) from exc


# ============================================================
# 2. APPLY DISRUPTION + REPLAN
# ============================================================

@router.post(
    "/replan",
    response_model=ReplanResponse,
    status_code=status.HTTP_200_OK,
)
def replan_itinerary(
    trip_id: str,
    payload: Optional[ReplanRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Apply a disruption and automatically replan the trip.

    Unlike /disruptions/simulate, this endpoint MODIFIES
    the database.

    Typical flow:

        Disruption
            ↓
        Identify affected activity
            ↓
        Detect schedule/budget conflict
            ↓
        Find alternatives
            ↓
        Modify itinerary
            ↓
        Recalculate spending
            ↓
        Save changes
            ↓
        Resolve disruption

    The actual replanning logic is handled by
    default_disruption_manager.
    """

    # --------------------------------------------------------
    # Validate trip
    # --------------------------------------------------------

    _get_trip_or_404(
        trip_id=trip_id,
        db=db,
    )

    # --------------------------------------------------------
    # Handle optional request body
    # --------------------------------------------------------

    request_data = payload or ReplanRequest()

    # --------------------------------------------------------
    # Clean optional values
    # --------------------------------------------------------

    activity_id = _clean_optional_string(
        request_data.activity_id
    )

    title = _clean_optional_string(
        request_data.title
    )

    disruption_time = _clean_optional_string(
        request_data.time
    )

    disruption_type = (
        request_data.disruption_type
        or "activity_cancelled"
    )

    # --------------------------------------------------------
    # Execute replanning
    # --------------------------------------------------------

    try:
        replan_result = (
            default_disruption_manager.replan_and_apply(
                trip_id=trip_id,
                disruption_type=disruption_type,
                activity_id=activity_id,
                title=title,
                time=disruption_time,
                delay_minutes=request_data.delay_minutes or 0,
                cost_delta=request_data.cost_delta or 0.0,
                new_budget=request_data.new_budget,
                new_interests=request_data.new_interests,
                db=db,
            )
        )

        # ----------------------------------------------------
        # Validate required result fields
        # ----------------------------------------------------

        required_fields = [
            "trip_id",
            "status",
            "disruptions_addressed",
            "summary_of_changes",
            "affected_itinerary_count",
            "updated_spending",
            "updated_itinerary",
        ]

        missing_fields = [
            field
            for field in required_fields
            if field not in replan_result
        ]

        if missing_fields:
            raise ValueError(
                "Replanning engine returned an incomplete response. "
                f"Missing fields: {', '.join(missing_fields)}"
            )

        # ----------------------------------------------------
        # Convert itinerary items to API response models
        # ----------------------------------------------------

        updated_itinerary = []

        for item in replan_result["updated_itinerary"]:
            try:
                updated_itinerary.append(
                    ItineraryItemResponse.model_validate(item)
                )
            except Exception:
                # If SQLAlchemy objects are returned instead of
                # dictionaries, Pydantic's from_attributes config
                # should handle them.
                updated_itinerary.append(
                    ItineraryItemResponse.model_validate(
                        item,
                        from_attributes=True,
                    )
                )

        # ----------------------------------------------------
        # Build final API response
        # ----------------------------------------------------

        return ReplanResponse(
            trip_id=replan_result["trip_id"],
            status=replan_result["status"],
            disruptions_addressed=(
                replan_result["disruptions_addressed"]
            ),
            summary_of_changes=(
                replan_result["summary_of_changes"]
            ),
            affected_itinerary_count=(
                replan_result["affected_itinerary_count"]
            ),
            updated_spending=(
                replan_result["updated_spending"]
            ),
            budget_impact=(
                replan_result.get("budget_impact")
            ),
            travel_impact=(
                replan_result.get("travel_impact")
            ),
            changes_made=(
                replan_result.get("changes_made", [])
            ),
            recommended_alternative=(
                replan_result.get(
                    "recommended_alternative"
                )
            ),
            updated_itinerary=updated_itinerary,
        )

    except ValueError as exc:
        # ----------------------------------------------------
        # Client/request/replanning validation error
        # ----------------------------------------------------

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # ----------------------------------------------------
        # Unexpected server-side error
        # ----------------------------------------------------

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Replanning execution failed. "
                f"Details: {str(exc)}"
            ),
        ) from exc