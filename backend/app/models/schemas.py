from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# --- Activity Schemas ---
class ActivityBase(BaseModel):
    title: str
    category: str
    destination: str
    description: Optional[str] = None
    location: Optional[str] = None
    estimated_duration: Optional[str] = "1h 30m"
    cost: float = 0.0
    currency: str = "INR"
    rating: Optional[float] = 4.5
    image_url: Optional[str] = None


class ActivityCreate(ActivityBase):
    pass


class ActivityResponse(ActivityBase):
    id: str

    model_config = ConfigDict(from_attributes=True)


# --- Itinerary Item Schemas ---
class ItineraryItemBase(BaseModel):
    day_number: int = 1
    date: str
    time: str
    title: str
    category: Optional[str] = "Sightseeing"
    duration: Optional[str] = "1h 30m"
    location: Optional[str] = None
    cost: float = 0.0
    currency: str = "INR"
    transportation: Optional[str] = "Metro"
    status: str = "Confirmed"
    notes: Optional[str] = None
    order: int = 0


class ItineraryItemCreate(ItineraryItemBase):
    trip_id: Optional[str] = None


class ItineraryItemResponse(ItineraryItemBase):
    id: str
    trip_id: str

    model_config = ConfigDict(from_attributes=True)


class ItineraryDayGroup(BaseModel):
    day_number: int
    date: str
    title: str
    total_cost: float
    activities: List[ItineraryItemResponse]


class ItineraryResponse(BaseModel):
    trip_id: str
    destination: str
    total_days: int
    total_activities: int
    days: List[ItineraryDayGroup]


class ItineraryUpdateRequest(BaseModel):
    items: List[ItineraryItemBase]


# --- Booking Schemas ---
class BookingBase(BaseModel):
    booking_type: str
    provider: str
    reference_code: Optional[str] = None
    title: str
    cost: float = 0.0
    currency: str = "INR"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: str = "Confirmed"
    details: Optional[str] = None


class BookingCreate(BookingBase):
    trip_id: str


class BookingResponse(BookingBase):
    id: str
    trip_id: str

    model_config = ConfigDict(from_attributes=True)


# --- Budget Schemas ---
class BudgetBreakdown(BaseModel):
    accommodation: float = 0.0
    transportation: float = 0.0
    activities: float = 0.0
    food: float = 0.0
    miscellaneous: float = 0.0


class BudgetResponse(BaseModel):
    trip_id: str
    destination: str
    total_budget: float
    currency: str
    estimated_spending: float
    remaining_budget: float
    percent_utilized: float
    breakdown: BudgetBreakdown
    status: str  # healthy, warning, critical

    model_config = ConfigDict(from_attributes=True)


# --- Disruption Schemas ---
class DisruptionBase(BaseModel):
    disruption_type: str  # cancellation, delay, hotel, budget, custom
    title: str
    severity: str = "warning"  # critical, warning, info
    description: str
    ai_resolution: Optional[str] = None
    timestamp: str
    resolved: bool = False


class DisruptionSimulateRequest(BaseModel):
    disruption_type: str = Field(
        "activity_cancelled",
        description="Type of disruption: activity_cancelled, transportation_delayed, hotel_unavailable, budget_reduced, activity_unavailable, user_interests_changed, or user_added_activity",
    )
    title: Optional[str] = Field(None, description="Name of activity or disruption title (e.g. 'Louvre Museum')")
    description: Optional[str] = None
    severity: Optional[str] = "warning"
    activity_id: Optional[str] = Field(None, description="Optional specific activity ID (e.g. 'act-paris-001')")
    time: Optional[str] = Field(None, description="Scheduled start time affected (e.g. '10:00')")
    delay_minutes: Optional[int] = Field(0, description="Transit delay duration in minutes")
    cost_delta: Optional[float] = Field(0.0, description="Cost change or reduction amount")
    new_budget: Optional[float] = Field(None, description="Explicit new budget ceiling")
    new_interests: Optional[List[str]] = Field(None, description="Updated interest list")


class DisruptionSimulationResponse(BaseModel):
    simulation_mode: bool = True
    trip_id: str
    disruption_type: str
    reason_for_disruption: str
    affected_items: List[Dict[str, Any]] = []
    downstream_impacts: List[Dict[str, Any]] = []
    alternatives: List[Dict[str, Any]] = []
    recommended_alternative: Optional[Dict[str, Any]] = None
    updated_itinerary: List[Dict[str, Any]] = []
    budget_impact: Dict[str, Any] = {}
    travel_impact: Dict[str, Any] = {}
    changes_made: List[str] = []
    constraint_status: Optional[Dict[str, Any]] = None


class ReplanRequest(BaseModel):
    disruption_type: Optional[str] = "activity_cancelled"
    title: Optional[str] = None
    activity_id: Optional[str] = None
    time: Optional[str] = None
    delay_minutes: Optional[int] = 0
    cost_delta: Optional[float] = 0.0
    new_budget: Optional[float] = None
    new_interests: Optional[List[str]] = None


class DisruptionResponse(DisruptionBase):
    id: str
    trip_id: str

    model_config = ConfigDict(from_attributes=True)


class ReplanResponse(BaseModel):
    trip_id: str
    status: str
    disruptions_addressed: int
    summary_of_changes: str
    affected_itinerary_count: int
    updated_spending: float
    updated_itinerary: List[ItineraryItemResponse]
    budget_impact: Optional[Dict[str, Any]] = None
    travel_impact: Optional[Dict[str, Any]] = None
    changes_made: Optional[List[str]] = []
    recommended_alternative: Optional[Dict[str, Any]] = None



import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# --- Trip Schemas ---
class TripBase(BaseModel):
    destination: str = Field(..., min_length=1, description="Destination city or country")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    budget: float = Field(0.0, ge=0.0, description="Total budget ceiling")
    currency: str = "INR"
    travelers: int = Field(1, ge=1, le=100, description="Number of travelers")
    interests: Optional[List[str]] = []
    travel_style: Optional[str] = "Balanced"
    transport_preference: Optional[str] = "Public Transit"

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Destination cannot be empty or whitespace.")
        return cleaned

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            datetime.date.fromisoformat(v.strip())
        except Exception:
            raise ValueError(f"Invalid date format '{v}'. Expected YYYY-MM-DD.")
        return v.strip()

    @model_validator(mode="after")
    def validate_date_order(self):
        s = datetime.date.fromisoformat(self.start_date)
        e = datetime.date.fromisoformat(self.end_date)
        if e < s:
            raise ValueError(f"End date ({self.end_date}) cannot be before start date ({self.start_date}).")
        return self


class TripCreate(TripBase):
    auto_generate_itinerary: bool = True


class TripUpdate(BaseModel):
    destination: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget: Optional[float] = Field(None, ge=0.0)
    currency: Optional[str] = None
    travelers: Optional[int] = Field(None, ge=1, le=100)
    interests: Optional[List[str]] = None
    travel_style: Optional[str] = None
    transport_preference: Optional[str] = None
    status: Optional[str] = None

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_update_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                datetime.date.fromisoformat(v.strip())
            except Exception:
                raise ValueError(f"Invalid date format '{v}'. Expected YYYY-MM-DD.")
            return v.strip()
        return v


class TripResponse(BaseModel):
    id: str
    destination: str
    start_date: str
    end_date: str
    budget: float
    currency: str
    spending: float
    remaining_budget: float
    travelers: int
    interests: List[str]
    travel_style: Optional[str]
    transport_preference: Optional[str]
    status: str
    total_days: int
    active_alerts_count: int
    itinerary_preview_count: int

    model_config = ConfigDict(from_attributes=True)


# --- Assistant Chat Schemas ---
class ChatMessageRequest(BaseModel):
    message: str
    trip_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    id: str
    sender: str  # user or ai
    message: str
    timestamp: str
    suggestions: List[str] = []
    intent: Optional[str] = None
    action_type: Optional[str] = None
    explanation: Optional[str] = None


class ChatResponse(BaseModel):
    status: str
    intent: Optional[str] = None
    action_type: Optional[str] = None
    user_message: ChatMessageResponse
    ai_response: ChatMessageResponse

