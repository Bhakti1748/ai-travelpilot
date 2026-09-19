import datetime
import json
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.db_models import (
    ActivityModel,
    BookingModel,
    BudgetModel,
    ChatMessageModel,
    DisruptionModel,
    ItineraryItemModel,
    TripModel,
)


# ============================================================
# Utility Functions
# ============================================================

def parse_interests(interests_str: Optional[str]) -> List[str]:
    """Convert stored interests into a Python list."""
    if not interests_str:
        return []

    try:
        data = json.loads(interests_str)

        if isinstance(data, list):
            return [
                str(item).strip()
                for item in data
                if str(item).strip()
            ]
    except Exception:
        pass

    return [
        item.strip()
        for item in interests_str.split(",")
        if item.strip()
    ]


def format_interests(
    interests_list: Optional[List[str]],
) -> str:
    """Convert interests list to JSON string."""
    if not interests_list:
        return ""

    return json.dumps(interests_list)


def normalize_text(value: Any) -> str:
    """Normalize text for comparisons."""
    if value is None:
        return ""

    return str(value).strip().lower()


def duration_to_minutes(
    duration: Optional[str],
) -> int:
    """Convert strings such as '2h 30m' into minutes."""
    if not duration:
        return 60

    text = normalize_text(duration)

    hours = 0
    minutes = 0

    try:
        if "h" in text:
            hour_part = text.split("h")[0].strip()

            if hour_part:
                hours = int(hour_part)

        if "m" in text:
            minute_part = text.split("h")[-1]
            minute_part = minute_part.replace("m", "").strip()

            if minute_part:
                minutes = int(minute_part)

    except Exception:
        return 60

    total = hours * 60 + minutes

    return total if total > 0 else 60


def time_to_minutes(
    value: Optional[str],
) -> int:
    """Convert HH:MM or 12-hour time into minutes."""
    if not value:
        return 0

    value = str(value).strip()

    try:
        parsed = datetime.datetime.strptime(
            value,
            "%H:%M",
        )

        return parsed.hour * 60 + parsed.minute

    except Exception:
        pass

    try:
        parsed = datetime.datetime.strptime(
            value,
            "%I:%M %p",
        )

        return parsed.hour * 60 + parsed.minute

    except Exception:
        return 0


def minutes_to_time(total_minutes: int) -> str:
    """Convert minutes to HH:MM."""
    total_minutes = max(0, int(total_minutes))

    hours = (total_minutes // 60) % 24
    minutes = total_minutes % 60

    return f"{hours:02d}:{minutes:02d}"


# ============================================================
# Budget Helpers
# ============================================================

def calculate_budget_total(
    trip: TripModel,
) -> float:
    """
    Calculate total estimated trip spending from
    structured budget components.

    This is the main source of truth for budget calculations.
    """

    budget_record = getattr(
        trip,
        "budget_record",
        None,
    )

    if not budget_record:
        return float(
            getattr(trip, "spending", 0.0) or 0.0
        )

    components = [
        "accommodation",
        "transportation",
        "activities",
        "food",
        "miscellaneous",
    ]

    total = 0.0

    for field in components:
        total += float(
            getattr(
                budget_record,
                field,
                0.0,
            )
            or 0.0
        )

    return round(total, 2)


def sync_trip_spending(
    trip: TripModel,
) -> float:
    """
    Synchronize trip.spending with the structured budget.

    Spending is based on the complete budget rather than
    itinerary activity costs alone.
    """

    total = calculate_budget_total(trip)

    trip.spending = total

    if getattr(trip, "budget_record", None):
        trip.budget_record.estimated_spending = total

    return total


def get_budget_status(
    budget: float,
    spending: float,
) -> Dict[str, Any]:
    """Return structured budget information."""

    budget = float(budget or 0.0)
    spending = float(spending or 0.0)

    remaining = budget - spending

    if budget <= 0:
        percentage = 0.0
    else:
        percentage = (
            spending / budget
        ) * 100

    if remaining > 0:
        status = "under_budget"
    elif remaining == 0:
        status = "at_budget"
    else:
        status = "over_budget"

    return {
        "budget": round(budget, 2),
        "spending": round(spending, 2),
        "remaining": round(remaining, 2),
        "percentage_used": round(
            percentage,
            2,
        ),
        "status": status,
    }


# ============================================================
# Database Seeding
# ============================================================

def seed_database(
    db: Session,
) -> None:
    """
    Initialize the database without creating a hardcoded
    destination or demo itinerary.

    TravelPilot is destination-independent.

    Activities are obtained dynamically through Geoapify
    when a real trip itinerary is generated.

    This function is intentionally kept safe to call from
    application startup.
    """

    # --------------------------------------------------------
    # IMPORTANT
    # --------------------------------------------------------
    # Do NOT insert hardcoded activities here.
    #
    # The application now uses:
    #
    # User destination
    #       ↓
    # Geoapify Places API
    #       ↓
    # Dynamic activities
    #       ↓
    # AI Trip Planner
    #       ↓
    # Itinerary
    #
    # Therefore there is no Paris catalog and no demo trip.
    # --------------------------------------------------------

    return


# ============================================================
# Itinerary Generation
# ============================================================

def generate_itinerary_for_trip(
    trip: TripModel,
    db: Session,
) -> List[ItineraryItemModel]:
    """
    Generate an itinerary using the Trip Planner Agent.

    The destination comes directly from the current trip.

    No destination is hardcoded here.

    Geoapify is responsible for retrieving activities
    for the requested destination.
    """

    from app.agents.trip_planner import plan_itinerary

    if not trip.destination:
        raise ValueError(
            "Trip destination is required before generating an itinerary."
        )

    # --------------------------------------------------------
    # Remove existing itinerary
    # --------------------------------------------------------

    (
        db.query(ItineraryItemModel)
        .filter(
            ItineraryItemModel.trip_id == trip.id
        )
        .delete(
            synchronize_session=False
        )
    )

    interests = parse_interests(
        trip.interests
    )

    # --------------------------------------------------------
    # Generate dynamic itinerary
    # --------------------------------------------------------

    plan_result = plan_itinerary(
        destination=trip.destination,
        start_date=trip.start_date,
        end_date=trip.end_date,
        budget=trip.budget,
        travelers=trip.travelers,
        interests=interests,
        travel_style=(
            trip.travel_style
            or "Balanced"
        ),
        transportation_preference=(
            trip.transport_preference
            or "Public Transit"
        ),
    )

    created_items = []

    activity_total = 0.0
    food_total = 0.0

    order_idx = 1

    # --------------------------------------------------------
    # Convert planner result into database itinerary
    # --------------------------------------------------------

    for day in plan_result.get(
        "days",
        [],
    ):
        day_num = day.get(
            "day_number",
            1,
        )

        for act in day.get(
            "activities",
            [],
        ):
            cost = float(
                act.get(
                    "estimated_cost",
                    0.0,
                )
                or 0.0
            )

            category = act.get(
                "category",
                "Sightseeing",
            )

            item = ItineraryItemModel(
                id=(
                    f"item-{trip.id}-"
                    f"{day_num}-{order_idx}"
                ),

                trip_id=trip.id,

                day_number=day_num,

                date=act.get(
                    "date",
                    trip.start_date,
                ),

                time=act.get(
                    "start_time",
                    "09:30",
                ),

                title=act.get(
                    "activity_name",
                    "Curated Experience",
                ),

                category=category,

                duration=act.get(
                    "duration",
                    "1h 30m",
                ),

                location=act.get(
                    "location",
                    trip.destination,
                ),

                cost=cost,

                currency=(
                    trip.currency
                    or "USD"
                ),

                transportation=act.get(
                    "transportation",
                    trip.transport_preference
                    or "Public Transit",
                ),

                status="Confirmed",

                notes=act.get(
                    "reason",
                    "Selected by AI trip planner.",
                ),

                order=order_idx,
            )

            db.add(item)

            created_items.append(item)

            # ------------------------------------------------
            # Budget classification
            # ------------------------------------------------

            if normalize_text(category) == "food":
                food_total += cost
            else:
                activity_total += cost

            order_idx += 1

    db.flush()

    # --------------------------------------------------------
    # Update structured budget
    # --------------------------------------------------------

    if trip.budget_record:

        trip.budget_record.activities = (
            activity_total
        )

        trip.budget_record.food = (
            food_total
        )

        sync_trip_spending(trip)

    else:

        trip.spending = (
            activity_total
            + food_total
        )

    db.commit()

    return created_items


# ============================================================
# Disruption Simulation
# ============================================================

def simulate_disruption_for_trip(
    trip_id: str,
    disruption_type: str,
    title: Optional[str],
    description: Optional[str],
    severity: str,
    cost_delta: float,
    db: Session,
) -> DisruptionModel:

    trip = (
        db.query(TripModel)
        .filter(
            TripModel.id == trip_id
        )
        .first()
    )

    if not trip:
        raise ValueError(
            f"Trip with ID {trip_id} not found"
        )

    disruption_type = (
        disruption_type
        or "custom"
    ).strip().lower()

    resolutions = {
        "cancellation": (
            "TravelPilot detected an unavailable "
            "activity and will search for a compatible "
            "replacement."
        ),

        "delay": (
            "TravelPilot detected a transportation "
            "delay and will shift affected itinerary "
            "items."
        ),

        "hotel": (
            "TravelPilot detected an accommodation "
            "issue and will review the trip plan."
        ),

        "budget": (
            "TravelPilot detected a budget change "
            "and will identify lower-cost options."
        ),

        "activity_unavailable": (
            "TravelPilot detected an unavailable "
            "activity and will identify alternatives."
        ),

        "weather": (
            "TravelPilot detected a weather-related "
            "disruption and will review outdoor "
            "activities and backup options."
        ),

        "custom": (
            "TravelPilot evaluated the simulated "
            "travel disruption."
        ),
    }

    ai_resolution = resolutions.get(
        disruption_type,
        resolutions["custom"],
    )

    event_title = (
        title
        or (
            f"{disruption_type.capitalize()} "
            "Anomaly Detected"
        )
    )

    event_description = (
        description
        or (
            f"A simulated {disruption_type} "
            "event occurred."
        )
    )

    disruption = DisruptionModel(
        id=(
            f"disruption-"
            f"{uuid.uuid4().hex[:8]}"
        ),

        trip_id=trip_id,

        disruption_type=disruption_type,

        title=event_title,

        severity=severity or "warning",

        description=event_description,

        ai_resolution=ai_resolution,

        timestamp=(
            datetime.datetime.now()
            .strftime("%I:%M %p")
        ),

        resolved=False,
    )

    db.add(disruption)

    # --------------------------------------------------------
    # Apply explicit cost change to miscellaneous budget
    # --------------------------------------------------------

    if (
        cost_delta
        and cost_delta != 0.0
        and trip.budget_record
    ):

        current_misc = float(
            trip.budget_record.miscellaneous
            or 0.0
        )

        trip.budget_record.miscellaneous = (
            current_misc + float(cost_delta)
        )

        sync_trip_spending(trip)

    db.commit()

    return disruption


# ============================================================
# Replanning Helpers
# ============================================================

def _find_affected_item(
    items: List[ItineraryItemModel],
    disruption: DisruptionModel,
) -> Optional[ItineraryItemModel]:
    """Find an itinerary item related to a disruption."""

    keywords = normalize_text(
        (
            disruption.title
            or ""
        )
        + " "
        + (
            disruption.description
            or ""
        )
    ).split()

    if not keywords:
        return items[0] if items else None

    best_item = None
    best_score = 0

    for item in items:

        item_text = normalize_text(
            f"{item.title} "
            f"{item.category} "
            f"{item.location}"
        )

        score = sum(
            1
            for keyword in keywords
            if len(keyword) > 3
            and keyword in item_text
        )

        if score > best_score:
            best_score = score
            best_item = item

    if best_item:
        return best_item

    return items[0] if items else None


def _find_replacement_activity(
    trip: TripModel,
    affected_item: Optional[ItineraryItemModel],
    db: Session,
) -> Optional[ActivityModel]:
    """
    Find a compatible replacement activity.

    First tries activities belonging to the current
    destination.

    This keeps disruption management destination-independent.
    """

    if not affected_item:
        return None

    # --------------------------------------------------------
    # Find activities for current destination
    # --------------------------------------------------------

    activities = (
        db.query(ActivityModel)
        .filter(
            ActivityModel.destination.ilike(
                f"%{trip.destination}%"
            )
        )
        .all()
    )

    # --------------------------------------------------------
    # If local database has no activities yet, return None.
    #
    # Dynamic activities should normally be generated
    # through Geoapify during itinerary generation.
    # --------------------------------------------------------

    if not activities:
        return None

    target_category = normalize_text(
        affected_item.category
    )

    candidates = []

    for activity in activities:

        if normalize_text(
            activity.title
        ) == normalize_text(
            affected_item.title
        ):
            continue

        category = normalize_text(
            activity.category
        )

        score = 0

        if (
            target_category
            and (
                target_category in category
                or category in target_category
            )
        ):
            score += 5

        rating = float(
            activity.rating or 0.0
        )

        score += rating

        candidates.append(
            (
                score,
                activity,
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    return candidates[0][1]


# ============================================================
# Replanning
# ============================================================

def replan_trip_itinerary(
    trip_id: str,
    db: Session,
) -> dict:
    """
    Resolve pending disruptions and adapt the itinerary.

    Uses only the current trip's data.
    No destination is hardcoded.
    """

    trip = (
        db.query(TripModel)
        .filter(
            TripModel.id == trip_id
        )
        .first()
    )

    if not trip:
        raise ValueError(
            f"Trip with ID {trip_id} not found"
        )

    disruptions = (
        db.query(DisruptionModel)
        .filter(
            DisruptionModel.trip_id == trip_id,
            DisruptionModel.resolved == False,
        )
        .order_by(
            DisruptionModel.id
        )
        .all()
    )

    items = (
        db.query(ItineraryItemModel)
        .filter(
            ItineraryItemModel.trip_id == trip_id
        )
        .order_by(
            ItineraryItemModel.day_number,
            ItineraryItemModel.order,
        )
        .all()
    )

    affected_count = 0
    replacement_count = 0
    resolved_count = 0

    actions = []

    # ========================================================
    # Process disruptions
    # ========================================================

    for disruption in disruptions:

        disruption_type = normalize_text(
            disruption.disruption_type
        )

        # ----------------------------------------------------
        # Cancellation / unavailable activity
        # ----------------------------------------------------

        if disruption_type in {
            "cancellation",
            "activity_unavailable",
        }:

            affected_item = _find_affected_item(
                items,
                disruption,
            )

            replacement = _find_replacement_activity(
                trip,
                affected_item,
                db,
            )

            if affected_item:

                old_title = affected_item.title

                affected_item.status = "Replaced"

                affected_count += 1

                if replacement:

                    affected_item.title = (
                        replacement.title
                    )

                    affected_item.category = (
                        replacement.category
                    )

                    affected_item.location = (
                        replacement.location
                        or trip.destination
                    )

                    affected_item.duration = (
                        replacement.estimated_duration
                        or "1h 30m"
                    )

                    affected_item.cost = float(
                        replacement.cost
                        or 0.0
                    )

                    affected_item.currency = (
                        replacement.currency
                        or trip.currency
                        or "USD"
                    )

                    affected_item.status = "Rerouted"

                    affected_item.notes = (
                        "Replaced automatically "
                        "after a simulated "
                        "activity disruption."
                    )

                    replacement_count += 1

                    actions.append(
                        {
                            "type": "replacement",

                            "old_activity": (
                                old_title
                            ),

                            "new_activity": (
                                replacement.title
                            ),
                        }
                    )

                else:

                    affected_item.notes = (
                        "Activity unavailable. "
                        "No compatible replacement "
                        "was found in the current "
                        "destination activity data."
                    )

                    actions.append(
                        {
                            "type": "replacement_unavailable",

                            "activity": (
                                old_title
                            ),
                        }
                    )

        # ----------------------------------------------------
        # Delay
        # ----------------------------------------------------

        elif disruption_type == "delay":

            delay_minutes = 45

            affected_item = _find_affected_item(
                items,
                disruption,
            )

            if affected_item:

                day = affected_item.day_number

                for item in items:

                    if item.day_number != day:
                        continue

                    current_time = time_to_minutes(
                        item.time
                    )

                    if (
                        item.order
                        >= affected_item.order
                    ):

                        item.time = minutes_to_time(
                            current_time
                            + delay_minutes
                        )

                        if item.status == "Confirmed":
                            item.status = "Delayed"

                        item.notes = (
                            (
                                item.notes
                                or ""
                            )
                            + " "
                            + (
                                "Adjusted by TravelPilot "
                                "to absorb a 45-minute "
                                "transport delay."
                            )
                        ).strip()

                        affected_count += 1

                actions.append(
                    {
                        "type": "delay",

                        "delay_minutes": delay_minutes,
                    }
                )

        # ----------------------------------------------------
        # Budget reduction
        # ----------------------------------------------------

        elif disruption_type == "budget":

            expensive_items = sorted(
                [
                    item
                    for item in items
                    if item.status
                    not in {
                        "Cancelled",
                        "Replaced",
                    }
                ],
                key=lambda item: float(
                    item.cost or 0.0
                ),
                reverse=True,
            )

            for item in expensive_items[:2]:

                if float(
                    item.cost or 0.0
                ) > 0:

                    item.notes = (
                        (
                            item.notes
                            or ""
                        )
                        + " Budget review flag: "
                        "consider lower-cost "
                        "alternative."
                    ).strip()

                    affected_count += 1

            actions.append(
                {
                    "type": "budget_review",

                    "message": (
                        "Expensive itinerary items "
                        "were flagged for lower-cost "
                        "alternatives."
                    ),
                }
            )

        # ----------------------------------------------------
        # Hotel disruption
        # ----------------------------------------------------

        elif disruption_type in {
            "hotel",
            "accommodation",
        }:

            affected_count += 1

            actions.append(
                {
                    "type": "hotel_review",

                    "message": (
                        "Accommodation issue detected. "
                        "Trip remains active while an "
                        "alternative stay is evaluated."
                    ),
                }
            )

        # ----------------------------------------------------
        # Weather
        # ----------------------------------------------------

        elif disruption_type == "weather":

            for item in items:

                category = normalize_text(
                    item.category
                )

                if category in {
                    "nature",
                    "outdoor",
                    "photography",
                }:

                    item.notes = (
                        (
                            item.notes
                            or ""
                        )
                        + " Weather backup recommended."
                    ).strip()

                    affected_count += 1

            actions.append(
                {
                    "type": "weather_backup",

                    "message": (
                        "Outdoor activities were "
                        "flagged for indoor alternatives."
                    ),
                }
            )

        # ----------------------------------------------------
        # Generic/custom disruption
        # ----------------------------------------------------

        else:

            actions.append(
                {
                    "type": "review",

                    "message": (
                        "TravelPilot reviewed the "
                        "disruption and preserved "
                        "the remaining itinerary."
                    ),
                }
            )

        disruption.resolved = True

        resolved_count += 1

    # ========================================================
    # Recalculate structured budget
    # ========================================================

    if trip.budget_record:
        sync_trip_spending(trip)

    db.commit()

    budget_total = float(
        trip.budget or 0.0
    )

    spending_total = float(
        trip.spending or 0.0
    )

    return {
        "status": "success",

        "trip_id": trip_id,

        "disruptions_processed": len(
            disruptions
        ),

        "disruptions_resolved": resolved_count,

        "affected_items": affected_count,

        "replacements": replacement_count,

        "remaining_budget": round(
            budget_total
            - spending_total,
            2,
        ),

        "actions": actions,
    }


# ============================================================
# Assistant Chat
# ============================================================

def handle_assistant_chat(
    message: str,
    trip_id: Optional[str],
    db: Session,
) -> dict:
    """
    Deterministic TravelPilot assistant.

    Uses actual database trip, budget, itinerary and
    booking information.

    It is destination-independent and works with the
    currently selected trip.
    """

    # ========================================================
    # 1. Find trip
    # ========================================================

    trip = None

    if trip_id:

        trip = (
            db.query(TripModel)
            .filter(
                TripModel.id == trip_id
            )
            .first()
        )

    # ========================================================
    # 2. Default values
    # ========================================================

    if trip:

        destination = (
            trip.destination
            or "your destination"
        )

        currency = (
            trip.currency
            or "USD"
        )

        budget = float(
            trip.budget
            or 0.0
        )

        if trip.budget_record:

            spending = calculate_budget_total(
                trip
            )

        else:

            spending = float(
                trip.spending
                or 0.0
            )

        trip.spending = spending

    else:

        destination = "your destination"

        currency = "USD"

        budget = 0.0

        spending = 0.0

    # ========================================================
    # 3. Budget status
    # ========================================================

    remaining = budget - spending

    budget_info = get_budget_status(
        budget,
        spending,
    )

    # ========================================================
    # 4. Normalize message
    # ========================================================

    lower = (
        message.lower().strip()
        if message
        else ""
    )

    suggestions = []

    # ========================================================
    # BUDGET
    # ========================================================

    if (
        "budget" in lower
        or "cost" in lower
        or "save" in lower
        or "spend" in lower
        or "spent" in lower
        or "remaining" in lower
        or "left" in lower
    ):

        if not trip:

            ai_text = (
                "Please provide a valid trip "
                "so I can calculate your "
                "current budget."
            )

            suggestions = [
                "Create a trip",
                "Plan a trip",
            ]

        elif remaining > 0:

            ai_text = (
                f"You have {currency} "
                f"{remaining:,.2f} remaining "
                f"from your {currency} "
                f"{budget:,.2f} trip budget. "
                f"Your current estimated "
                f"spending is {currency} "
                f"{spending:,.2f}."
            )

            suggestions = [
                "How much have I spent?",
                "Find cheaper activities",
                "Show my budget breakdown",
            ]

        elif remaining == 0:

            ai_text = (
                f"You have reached your trip "
                f"budget of {currency} "
                f"{budget:,.2f}. "
                f"Current estimated spending "
                f"is {currency} "
                f"{spending:,.2f}."
            )

            suggestions = [
                "Find free activities",
                "Find cheaper activities",
                "Show my budget breakdown",
            ]

        else:

            over_budget = abs(
                remaining
            )

            ai_text = (
                f"Your current estimated trip "
                f"spending is {currency} "
                f"{spending:,.2f}, which is "
                f"{currency} "
                f"{over_budget:,.2f} over your "
                f"{currency} "
                f"{budget:,.2f} budget. "
                "TravelPilot can look for "
                "lower-cost alternatives."
            )

            suggestions = [
                "Find cheaper activities",
                "Reduce my trip budget",
                "Replan to reduce spending",
            ]

    # ========================================================
    # WEATHER
    # ========================================================

    elif (
        "rain" in lower
        or "weather" in lower
        or "storm" in lower
        or "sunny" in lower
    ):

        ai_text = (
            f"I can help adapt your "
            f"{destination} itinerary "
            "for weather changes. "
            "Live weather data is not "
            "connected in the current "
            "prototype, so I won't claim "
            "a real-time forecast. "
            "If rain is expected, "
            "TravelPilot can prioritize "
            "museums, galleries, cafes "
            "and other indoor activities."
        )

        suggestions = [
            "Show indoor activities",
            "Create a rainy-day backup plan",
            "Replan the affected day",
        ]

    # ========================================================
    # TRANSPORT / DELAY
    # ========================================================

    elif (
        "delay" in lower
        or "metro" in lower
        or "train" in lower
        or "transport" in lower
        or "bus" in lower
        or "flight" in lower
    ):

        ai_text = (
            f"If transportation is delayed "
            f"during your {destination} trip, "
            "TravelPilot can simulate the "
            "disruption and shift affected "
            "itinerary items while attempting "
            "to preserve the rest of the schedule."
        )

        suggestions = [
            "Simulate a 30-minute delay",
            "Simulate a 60-minute delay",
            "Replan the affected day",
        ]

    # ========================================================
    # CANCELLATION
    # ========================================================

    elif (
        "cancel" in lower
        or "cancelled" in lower
        or "canceled" in lower
        or "unavailable" in lower
        or "closed" in lower
    ):

        ai_text = (
            f"If an activity becomes unavailable "
            f"in {destination}, TravelPilot can "
            "identify the affected itinerary "
            "item and search for a compatible "
            "alternative based on category, "
            "cost, location and rating."
        )

        suggestions = [
            "Simulate activity cancellation",
            "Find a replacement activity",
            "Replan my itinerary",
        ]

    # ========================================================
    # ITINERARY
    # ========================================================

    elif (
        "itinerary" in lower
        or "schedule" in lower
        or "planned" in lower
        or "activities" in lower
        or "activity" in lower
        or "tomorrow" in lower
        or "today" in lower
    ):

        if trip:

            items = (
                db.query(
                    ItineraryItemModel
                )
                .filter(
                    ItineraryItemModel.trip_id
                    == trip.id
                )
                .order_by(
                    ItineraryItemModel.day_number,
                    ItineraryItemModel.order,
                )
                .all()
            )

            active_items = [
                item
                for item in items
                if normalize_text(
                    item.status
                )
                not in {
                    "cancelled",
                    "canceled",
                }
            ]

            if active_items:

                preview_items = (
                    active_items[:5]
                )

                activity_text = "; ".join(
                    [
                        (
                            f"{item.time} - "
                            f"{item.title}"
                        )
                        for item in preview_items
                    ]
                )

                ai_text = (
                    f"Your {destination} "
                    f"itinerary currently contains "
                    f"{len(active_items)} active "
                    f"activities. Upcoming scheduled "
                    f"items include: "
                    f"{activity_text}."
                )

                if len(active_items) > 5:

                    ai_text += (
                        " I can help you review "
                        "the remaining activities "
                        "as well."
                    )

            else:

                ai_text = (
                    f"There are currently no "
                    f"active itinerary items for "
                    f"your {destination} trip."
                )

            suggestions = [
                "How much budget do I have left?",
                "Show today's activities",
                "Check for schedule conflicts",
            ]

        else:

            ai_text = (
                "I need a valid trip to "
                "review the itinerary."
            )

            suggestions = [
                "Create a trip",
                "Plan an itinerary",
            ]

    # ========================================================
    # HOTEL
    # ========================================================

    elif (
        "hotel" in lower
        or "accommodation" in lower
        or "stay" in lower
        or "room" in lower
    ):

        if trip:

            booking = (
                db.query(BookingModel)
                .filter(
                    BookingModel.trip_id
                    == trip.id,

                    BookingModel.booking_type.ilike(
                        "%hotel%"
                    ),
                )
                .first()
            )

            if booking:

                ai_text = (
                    f"Your current accommodation "
                    f"is {booking.provider or booking.title}. "
                    f"Booking status: "
                    f"{booking.status or 'Unknown'}."
                )

            else:

                ai_text = (
                    "I couldn't find a hotel "
                    "booking for this trip."
                )

        else:

            ai_text = (
                "Please provide a valid trip "
                "so I can check accommodation "
                "details."
            )

        suggestions = [
            "Check my itinerary",
            "Check my budget",
            "What if my hotel becomes unavailable?",
        ]

    # ========================================================
    # GENERAL QUERY
    # ========================================================

    else:

        if trip:

            if remaining >= 0:

                budget_summary = (
                    f"{currency} "
                    f"{remaining:,.2f} "
                    "remaining"
                )

            else:

                budget_summary = (
                    f"{currency} "
                    f"{abs(remaining):,.2f} "
                    "over budget"
                )

            ai_text = (
                f"Your {destination} trip "
                f"currently has "
                f"{budget_summary}. "
                f"Estimated spending is "
                f"{currency} "
                f"{spending:,.2f} out of "
                f"{currency} "
                f"{budget:,.2f}. "
                "I can help review your "
                "itinerary, budget, activities "
                "or simulated travel disruptions."
            )

        else:

            ai_text = (
                "I can help with itinerary "
                "planning, budget questions, "
                "activities and simulated "
                "travel disruptions."
            )

        suggestions = [
            "Show my itinerary",
            "Check my budget",
            "Simulate a travel disruption",
        ]

    # ========================================================
    # SAVE CHAT
    # ========================================================

    user_msg_id = (
        f"msg-u-{uuid.uuid4().hex[:8]}"
    )

    ai_msg_id = (
        f"msg-ai-{uuid.uuid4().hex[:8]}"
    )

    now_str = (
        datetime.datetime.now()
        .strftime("%I:%M %p")
    )

    user_db = ChatMessageModel(
        id=user_msg_id,

        trip_id=trip_id,

        sender="user",

        message=message,

        timestamp=now_str,
    )

    ai_db = ChatMessageModel(
        id=ai_msg_id,

        trip_id=trip_id,

        sender="ai",

        message=ai_text,

        timestamp=now_str,

        suggestions=json.dumps(
            suggestions
        ),
    )

    db.add(user_db)
    db.add(ai_db)

    db.commit()

    # ========================================================
    # API RESPONSE
    # ========================================================

    return {
        "status": "success",

        "intent": "general_query",

        "action_type": "info",

        "user_message": {
            "id": user_msg_id,

            "sender": "user",

            "message": message,

            "timestamp": now_str,

            "suggestions": [],

            "intent": None,

            "action_type": None,

            "explanation": None,
        },

        "ai_response": {
            "id": ai_msg_id,

            "sender": "ai",

            "message": ai_text,

            "timestamp": now_str,

            "suggestions": suggestions,

            "intent": None,

            "action_type": None,

            "explanation": None,
        },

        "budget_status": budget_info,
    }