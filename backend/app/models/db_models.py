import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.session import Base


class TripModel(Base):
    __tablename__ = "trips"

    id = Column(String, primary_key=True, index=True)
    destination = Column(String, nullable=False, index=True)
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=False)
    budget = Column(Float, nullable=False, default=0.0)
    currency = Column(String, nullable=False, default="INR")
    spending = Column(Float, nullable=False, default=0.0)
    travelers = Column(Integer, nullable=False, default=1)
    interests = Column(Text, nullable=True)  # Comma-separated or JSON list
    travel_style = Column(String, nullable=True, default="Balanced")
    transport_preference = Column(String, nullable=True, default="Public Transit")
    status = Column(String, nullable=False, default="active")  # active, completed, draft
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    itinerary_items = relationship(
        "ItineraryItemModel", back_populates="trip", cascade="all, delete-orphan"
    )
    budget_record = relationship(
        "BudgetModel",
        back_populates="trip",
        uselist=False,
        cascade="all, delete-orphan",
    )
    bookings = relationship(
        "BookingModel", back_populates="trip", cascade="all, delete-orphan"
    )
    disruptions = relationship(
        "DisruptionModel", back_populates="trip", cascade="all, delete-orphan"
    )
    messages = relationship(
        "ChatMessageModel", back_populates="trip", cascade="all, delete-orphan"
    )


class ActivityModel(Base):
    __tablename__ = "activities"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)  # History, Food, Photography, Museums, etc.
    destination = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    estimated_duration = Column(String, nullable=True, default="1h 30m")
    cost = Column(Float, nullable=False, default=0.0)
    currency = Column(String, nullable=False, default="INR")
    rating = Column(Float, nullable=True, default=4.5)
    image_url = Column(String, nullable=True)


class ItineraryItemModel(Base):
    __tablename__ = "itinerary_items"

    id = Column(String, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False, index=True)
    day_number = Column(Integer, nullable=False, default=1)
    date = Column(String, nullable=False)
    time = Column(String, nullable=False)  # "09:00"
    title = Column(String, nullable=False)
    category = Column(String, nullable=True)
    duration = Column(String, nullable=True, default="1h 30m")
    location = Column(String, nullable=True)
    cost = Column(Float, nullable=False, default=0.0)
    currency = Column(String, nullable=False, default="INR")
    transportation = Column(String, nullable=True, default="Metro")
    status = Column(String, nullable=False, default="Confirmed")  # Confirmed, In Progress, Delayed, Rerouted, Cancelled
    notes = Column(Text, nullable=True)
    order = Column(Integer, nullable=False, default=0)

    trip = relationship("TripModel", back_populates="itinerary_items")


class BookingModel(Base):
    __tablename__ = "bookings"

    id = Column(String, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False, index=True)
    booking_type = Column(String, nullable=False)  # Hotel, Flight, Train, Activity
    provider = Column(String, nullable=False)
    reference_code = Column(String, nullable=True)
    title = Column(String, nullable=False)
    cost = Column(Float, nullable=False, default=0.0)
    currency = Column(String, nullable=False, default="INR")
    start_time = Column(String, nullable=True)
    end_time = Column(String, nullable=True)
    status = Column(String, nullable=False, default="Confirmed")
    details = Column(Text, nullable=True)

    trip = relationship("TripModel", back_populates="bookings")


class BudgetModel(Base):
    __tablename__ = "budgets"

    id = Column(String, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False, unique=True)
    total_budget = Column(Float, nullable=False, default=0.0)
    currency = Column(String, nullable=False, default="INR")
    estimated_spending = Column(Float, nullable=False, default=0.0)
    accommodation = Column(Float, nullable=False, default=0.0)
    transportation = Column(Float, nullable=False, default=0.0)
    activities = Column(Float, nullable=False, default=0.0)
    food = Column(Float, nullable=False, default=0.0)
    miscellaneous = Column(Float, nullable=False, default=0.0)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)

    trip = relationship("TripModel", back_populates="budget_record")


class DisruptionModel(Base):
    __tablename__ = "disruptions"

    id = Column(String, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False, index=True)
    disruption_type = Column(String, nullable=False)  # cancellation, delay, hotel, budget, custom
    title = Column(String, nullable=False)
    severity = Column(String, nullable=False, default="warning")  # critical, warning, info
    description = Column(Text, nullable=False)
    ai_resolution = Column(Text, nullable=True)
    timestamp = Column(String, nullable=False)
    resolved = Column(Boolean, default=False)

    trip = relationship("TripModel", back_populates="disruptions")


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=True, index=True)
    sender = Column(String, nullable=False)  # user, ai
    message = Column(Text, nullable=False)
    timestamp = Column(String, nullable=False)
    suggestions = Column(Text, nullable=True)  # JSON or comma-delimited string
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    trip = relationship("TripModel", back_populates="messages")
