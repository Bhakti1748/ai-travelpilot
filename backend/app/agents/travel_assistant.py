"""
TravelPilot Conversational AI Assistant

Implements the conversational agent loop:

1. Understand user request & classify intent
2. Retrieve current trip state
3. Invoke appropriate tools/services
4. Generate a grounded response
5. Require explicit confirmation before applying itinerary changes
"""

import datetime
import json
import logging
import re
import uuid
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.agents.disruption_manager import default_disruption_manager
from app.database.session import SessionLocal
from app.models.db_models import (
    BookingModel,
    BudgetModel,
    ChatMessageModel,
    TripModel,
)
from app.services.constraint_engine import _minutes_to_time, _time_to_minutes
from app.services.dataset_service import dataset_service
from app.tools import default_tool_registry


logger = logging.getLogger(__name__)


class TravelAssistant:
    """
    Conversational AI Co-pilot for TravelPilot.
    """

    def __init__(self, db: Optional[Session] = None):
        self._external_db = db

    # ------------------------------------------------------------------
    # DATABASE
    # ------------------------------------------------------------------

    def _get_db(self) -> Session:
        """
        Return the provided database session or create a new one.
        """
        return (
            self._external_db
            if self._external_db is not None
            else SessionLocal()
        )

    # ------------------------------------------------------------------
    # BUDGET HELPERS
    # ------------------------------------------------------------------

    def _get_budget_snapshot(
        self,
        trip_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Calculate a consistent budget snapshot.

        We intentionally calculate committed spending from the
        BudgetModel category components instead of blindly trusting
        TripModel.spending.

        This prevents stale/corrupted trip.spending values from causing
        responses such as:

            Budget = INR 100,000
            Remaining = INR -18,500

        when the actual seeded budget components total INR 68,500.
        """

        trip = (
            db.query(TripModel)
            .filter(TripModel.id == trip_id)
            .first()
        )

        budget_record = (
            db.query(BudgetModel)
            .filter(BudgetModel.trip_id == trip_id)
            .first()
        )

        if not trip:
            return {
                "total_budget": 0.0,
                "total_spent": 0.0,
                "remaining_budget": 0.0,
                "percentage_spent": 0.0,
                "currency": "INR",
                "spending_status": "unknown",
                "categories": {
                    "accommodation": 0.0,
                    "activities": 0.0,
                    "transportation": 0.0,
                    "food": 0.0,
                    "miscellaneous": 0.0,
                },
            }

        total_budget = float(trip.budget or 0.0)
        currency = trip.currency or "INR"

        categories = {
            "accommodation": 0.0,
            "activities": 0.0,
            "transportation": 0.0,
            "food": 0.0,
            "miscellaneous": 0.0,
        }

        if budget_record:
            categories = {
                "accommodation": float(
                    budget_record.accommodation or 0.0
                ),
                "activities": float(
                    budget_record.activities or 0.0
                ),
                "transportation": float(
                    budget_record.transportation or 0.0
                ),
                "food": float(
                    budget_record.food or 0.0
                ),
                "miscellaneous": float(
                    budget_record.miscellaneous or 0.0
                ),
            }

        # The seeded/demo budget is represented by these components.
        # Using their sum keeps the assistant consistent with the
        # actual budget breakdown shown in the dashboard.
        total_spent = sum(categories.values())

        # If no category information exists, fall back to TripModel.
        if total_spent <= 0:
            total_spent = float(trip.spending or 0.0)

        remaining_budget = total_budget - total_spent

        if total_budget > 0:
            percentage_spent = round(
                (total_spent / total_budget) * 100,
                1,
            )
        else:
            percentage_spent = 0.0

        if remaining_budget < 0:
            spending_status = "over_budget"
        elif percentage_spent >= 90:
            spending_status = "near_limit"
        elif percentage_spent >= 70:
            spending_status = "moderate"
        else:
            spending_status = "healthy"

        return {
            "total_budget": total_budget,
            "total_spent": total_spent,
            "remaining_budget": remaining_budget,
            "percentage_spent": percentage_spent,
            "currency": currency,
            "spending_status": spending_status,
            "categories": categories,
        }

    # ------------------------------------------------------------------
    # AGENT STEP 1
    # INTENT CLASSIFICATION
    # ------------------------------------------------------------------

    def classify_intent(
        self,
        message: str,
        last_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Classify the user's message into a TravelPilot intent.
        """

        m = message.lower().strip()

        clean_m = re.sub(r"[^\w\s]", "", m).strip()

        # --------------------------------------------------------------
        # Confirmation intent
        # --------------------------------------------------------------

        confirmation_phrases = (
            "apply it",
            "apply",
            "yes apply",
            "yes",
            "yes apply it",
            "apply changes",
            "confirm",
            "proceed",
            "do it",
            "go ahead",
        )

        if clean_m in confirmation_phrases:
            return "confirm_apply"

        # Only treat "apply" as confirmation when it is clearly being
        # used as a confirmation rather than a general question.
        if (
            "apply changes" in clean_m
            or "apply it" in clean_m
            or "yes apply" in clean_m
        ):
            return "confirm_apply"

        # --------------------------------------------------------------
        # Disruption / What-if simulation
        # --------------------------------------------------------------

        disruption_words = (
            "what if",
            "what happens if",
            "cancelled",
            "canceled",
            "closed",
            "delay",
            "delayed",
            "unavailable",
            "booking cancelled",
            "booking canceled",
            "transport delayed",
            "hotel unavailable",
        )

        if any(word in m for word in disruption_words):
            return "disruption_simulation"

        # --------------------------------------------------------------
        # Budget queries
        # --------------------------------------------------------------

        budget_query_phrases = (
            "how much have i spent",
            "how much did i spend",
            "how much spent",
            "how much am i spending",
            "how much budget do i have",
            "how much budget do i have left",
            "how much budget is left",
            "how much money do i have left",
            "how much do i have left",
            "budget left",
            "remaining budget",
            "remaining money",
            "money left",
            "budget remaining",
            "budget status",
            "my budget",
            "trip budget",
            "current budget",
            "total spending",
            "total spent",
            "spending",
            "expenses",
            "expenditure",
        )

        if any(phrase in m for phrase in budget_query_phrases):
            return "budget_query"

        # A plain "how much" + "budget" should also be a budget query.
        if "budget" in m and (
            "how much" in m
            or "left" in m
            or "remaining" in m
            or "spent" in m
        ):
            return "budget_query"

        # --------------------------------------------------------------
        # Budget adjustment
        # --------------------------------------------------------------

        budget_reduction_phrases = (
            "reduce my budget",
            "reduce budget",
            "cut budget",
            "lower budget",
            "trim budget",
            "increase my budget",
            "increase budget",
            "change my budget",
            "set my budget",
            "update my budget",
            "change budget",
        )

        if any(
            phrase in m
            for phrase in budget_reduction_phrases
        ):
            return "budget_adjustment"

        if "budget" in m and any(
            char.isdigit() for char in m
        ):
            return "budget_adjustment"

        # --------------------------------------------------------------
        # Proximity queries
        # --------------------------------------------------------------

        proximity_phrases = (
            "close to my hotel",
            "near my hotel",
            "near hotel",
            "around my hotel",
            "near the",
            "close to",
            "nearby",
            "near me",
            "walking distance",
        )

        if any(
            phrase in m
            for phrase in proximity_phrases
        ):
            return "proximity_query"

        # --------------------------------------------------------------
        # Schedule feasibility
        # --------------------------------------------------------------

        schedule_phrases = (
            "can i fit",
            "can we fit",
            "fit into",
            "add to schedule",
            "fit this activity",
            "can i add",
            "is there time",
            "do i have time",
        )

        if any(
            phrase in m
            for phrase in schedule_phrases
        ):
            return "schedule_feasibility"

        # --------------------------------------------------------------
        # Itinerary queries
        # --------------------------------------------------------------

        itinerary_phrases = (
            "tomorrow",
            "morning",
            "afternoon",
            "evening",
            "what should i do",
            "my plan",
            "my itinerary",
            "my schedule",
            "schedule for day",
            "today",
            "day 1",
            "day 2",
            "day 3",
            "day 4",
            "day 5",
            "what is planned",
        )

        if any(
            phrase in m
            for phrase in itinerary_phrases
        ):
            return "itinerary_query"

        # --------------------------------------------------------------
        # Interest queries
        # --------------------------------------------------------------

        interest_phrases = (
            "interest",
            "photography",
            "museum",
            "museums",
            "art",
            "food",
            "nature",
            "shopping",
            "historic",
            "history",
            "entertainment",
        )

        if any(
            phrase in m
            for phrase in interest_phrases
        ):
            return "interest_query"

        return "general_query"

    # ------------------------------------------------------------------
    # MAIN CHAT LOOP
    # ------------------------------------------------------------------

    def chat(
        self,
        message: str,
        trip_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Execute the TravelPilot conversational agent loop.

        Understand
            ->
        Retrieve trip state
            ->
        Select handler/tool
            ->
        Generate grounded response
            ->
        Persist conversation
        """

        active_db = db or self._get_db()

        try:
            # ----------------------------------------------------------
            # 1. Resolve active trip
            # ----------------------------------------------------------

            trip = None

            if trip_id:
                trip = (
                    active_db.query(TripModel)
                    .filter(TripModel.id == trip_id)
                    .first()
                )

            if not trip:
                trip = (
                    active_db.query(TripModel)
                    .first()
                )

            resolved_trip_id = (
                trip.id
                if trip
                else "trip-paris-demo-2026"
            )

            # ----------------------------------------------------------
            # 2. Retrieve previous AI message
            # ----------------------------------------------------------

            last_ai_msg = (
                active_db.query(ChatMessageModel)
                .filter(
                    ChatMessageModel.trip_id
                    == resolved_trip_id,
                    ChatMessageModel.sender == "ai",
                )
                .order_by(
                    ChatMessageModel.created_at.desc()
                )
                .first()
            )

            last_meta: Dict[str, Any] = {}

            if (
                last_ai_msg
                and last_ai_msg.suggestions
            ):
                try:
                    parsed_suggestions = json.loads(
                        last_ai_msg.suggestions
                    )

                    if isinstance(
                        parsed_suggestions,
                        dict,
                    ):
                        last_meta = parsed_suggestions

                    elif (
                        isinstance(
                            parsed_suggestions,
                            list,
                        )
                        and any(
                            "apply"
                            in str(item).lower()
                            for item in parsed_suggestions
                        )
                    ):
                        last_meta = {
                            "has_pending_proposal": True
                        }

                except Exception:
                    pass

            # ----------------------------------------------------------
            # 3. Classify intent
            # ----------------------------------------------------------

            intent = self.classify_intent(
                message,
                last_meta,
            )

            logger.info(
                "Classified message '%s' as intent: %s",
                message,
                intent,
            )

            # ----------------------------------------------------------
            # 4. Dispatch intent
            # ----------------------------------------------------------

            if intent == "confirm_apply":

                resp_data = self._handle_confirmation(
                    resolved_trip_id,
                    active_db,
                    last_ai_msg=last_ai_msg,
                )

            elif intent == "disruption_simulation":

                resp_data = (
                    self._handle_disruption_simulation(
                        message,
                        resolved_trip_id,
                        active_db,
                    )
                )

            elif intent == "itinerary_query":

                resp_data = self._handle_itinerary_query(
                    message,
                    resolved_trip_id,
                    active_db,
                )

            elif intent == "schedule_feasibility":

                resp_data = (
                    self._handle_schedule_feasibility(
                        message,
                        resolved_trip_id,
                        active_db,
                    )
                )

            elif intent == "proximity_query":

                resp_data = self._handle_proximity_query(
                    message,
                    resolved_trip_id,
                    active_db,
                )

            elif intent == "budget_query":

                resp_data = self._handle_budget_query(
                    resolved_trip_id,
                    active_db,
                )

            elif intent == "budget_adjustment":

                resp_data = (
                    self._handle_budget_adjustment(
                        message,
                        resolved_trip_id,
                        active_db,
                    )
                )

            elif intent == "interest_query":

                resp_data = self._handle_interest_query(
                    message,
                    resolved_trip_id,
                    active_db,
                )

            else:

                resp_data = self._handle_general_query(
                    message,
                    resolved_trip_id,
                    active_db,
                )

            # ----------------------------------------------------------
            # 5. Persist conversation
            # ----------------------------------------------------------

            now_str = datetime.datetime.now().strftime(
                "%I:%M %p"
            )

            user_msg_id = (
                f"msg-u-{uuid.uuid4().hex[:8]}"
            )

            ai_msg_id = (
                f"msg-ai-{uuid.uuid4().hex[:8]}"
            )

            user_record = ChatMessageModel(
                id=user_msg_id,
                trip_id=resolved_trip_id,
                sender="user",
                message=message,
                timestamp=now_str,
            )

            ai_record = ChatMessageModel(
                id=ai_msg_id,
                trip_id=resolved_trip_id,
                sender="ai",
                message=resp_data["message"],
                timestamp=now_str,
                suggestions=json.dumps(
                    resp_data.get(
                        "suggestions",
                        [],
                    )
                ),
            )

            active_db.add(user_record)
            active_db.add(ai_record)
            active_db.commit()

            # ----------------------------------------------------------
            # 6. Return API response
            # ----------------------------------------------------------

            return {
                "status": "success",
                "intent": intent,
                "action_type": resp_data.get(
                    "action_type",
                    "info",
                ),
                "user_message": {
                    "id": user_msg_id,
                    "sender": "user",
                    "message": message,
                    "timestamp": now_str,
                    "suggestions": [],
                },
                "ai_response": {
                    "id": ai_msg_id,
                    "sender": "ai",
                    "message": resp_data["message"],
                    "timestamp": now_str,
                    "suggestions": resp_data.get(
                        "suggestions",
                        [],
                    ),
                    "explanation": resp_data.get(
                        "explanation"
                    ),
                },
            }

        except Exception as exc:

            logger.exception(
                "TravelAssistant.chat failed: %s",
                exc,
            )

            try:
                active_db.rollback()
            except Exception:
                pass

            return {
                "status": "error",
                "message": (
                    "I encountered an issue while "
                    "processing your travel request."
                ),
                "error": str(exc),
            }

        finally:

            if (
                self._external_db is None
                and active_db
            ):
                active_db.close()

    # ------------------------------------------------------------------
    # ITINERARY QUERY
    # ------------------------------------------------------------------

    def _handle_itinerary_query(
        self,
        message: str,
        trip_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Answers questions such as:
        - What should I do tomorrow morning?
        - What is my plan for Day 2?
        """

        m = message.lower()

        day_target = 2 if "tomorrow" in m else 1

        if "day 1" in m:
            day_target = 1
        elif "day 2" in m:
            day_target = 2
        elif "day 3" in m:
            day_target = 3
        elif "day 4" in m:
            day_target = 4
        elif "day 5" in m:
            day_target = 5

        tool_res = default_tool_registry.execute(
            "get_current_itinerary",
            trip_id=trip_id,
            day_number=day_target,
        )

        if (
            not tool_res.get("success")
            or not tool_res.get("result", {}).get(
                "days"
            )
        ):
            return {
                "message": (
                    f"I couldn't find scheduled activities "
                    f"for Day {day_target}. "
                    "Would you like me to generate "
                    "activities for this day?"
                ),
                "suggestions": [
                    f"Generate Day {day_target} schedule",
                    "Check trip overview",
                ],
            }

        day_data = (
            tool_res["result"]["days"][0]
        )

        items = day_data.get("items", [])

        if "morning" in m:

            filtered = [
                item
                for item in items
                if _time_to_minutes(
                    item["time"]
                )
                < 12 * 60
            ]

            timeframe = "morning"

        elif "afternoon" in m:

            filtered = [
                item
                for item in items
                if 12 * 60
                <= _time_to_minutes(
                    item["time"]
                )
                < 17 * 60
            ]

            timeframe = "afternoon"

        elif "evening" in m:

            filtered = [
                item
                for item in items
                if _time_to_minutes(
                    item["time"]
                )
                >= 17 * 60
            ]

            timeframe = "evening"

        else:

            filtered = items
            timeframe = "full day"

        if not filtered:
            filtered = items[:2]

        if not filtered:
            return {
                "message": (
                    f"There are no activities currently "
                    f"scheduled for Day {day_target}."
                ),
                "suggestions": [
                    "Generate itinerary",
                    "Show trip overview",
                ],
            }

        lines = [
            (
                f"Here is your planned schedule for "
                f"Day {day_target} ({timeframe}):"
            ),
            "",
        ]

        for item in filtered:

            lines.append(
                f"- **{item['time']}**: "
                f"{item['title']} "
                f"({item.get('duration', '90m')}, "
                f"transit: "
                f"{item.get('transportation', 'Metro')})"
            )

        first_location = (
            filtered[0].get("location")
            if filtered
            else "city center"
        )

        lines.append(
            f"\nTip: Your first stop starts at "
            f"{first_location}."
        )

        lines.append(
            "TravelPilot keeps a transit buffer between stops."
        )

        return {
            "message": "\n".join(lines),
            "suggestions": [
                (
                    f"What's after "
                    f"{filtered[0]['title']}?"
                ),
                "Which cafes are nearby?",
                (
                    "Check schedule conflicts for "
                    f"Day {day_target}"
                ),
            ],
        }

    # ------------------------------------------------------------------
    # SCHEDULE FEASIBILITY
    # ------------------------------------------------------------------

    def _handle_schedule_feasibility(
        self,
        message: str,
        trip_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Answers:
        'Can I fit this activity into today's schedule?'
        """

        all_acts = dataset_service.all_activities

        if not all_acts:
            return {
                "message": (
                    "I couldn't find activity data "
                    "to perform the schedule check."
                ),
                "suggestions": [
                    "Show my itinerary",
                    "Find activities",
                ],
            }

        target_act = None
        message_lower = message.lower()

        for activity in all_acts:

            activity_name = str(
                activity.get("name", "")
            )

            words = [
                word
                for word in activity_name.lower().split()
                if len(word) > 4
            ]

            if (
                activity_name.lower()
                in message_lower
                or any(
                    word in message_lower
                    for word in words
                )
            ):
                target_act = activity
                break

        if not target_act:
            target_act = all_acts[0]

        open_res = default_tool_registry.execute(
            "check_opening_hours",
            activity_id=target_act["id"],
            time="14:00",
            duration_minutes=target_act.get(
                "duration_minutes",
                90,
            ),
        )

        itin_res = default_tool_registry.execute(
            "get_current_itinerary",
            trip_id=trip_id,
            day_number=1,
        )

        if (
            itin_res.get("success")
            and itin_res.get("result", {}).get("days")
        ):
            day_items = (
                itin_res["result"]["days"][0]
                .get("items", [])
            )
        else:
            day_items = []

        hours_ok = (
            open_res.get("result", {})
            .get("is_open", True)
        )

        duration_minutes = int(
            target_act.get(
                "duration_minutes",
                90,
            )
        )

        start_minutes = 14 * 60 + 30
        end_minutes = (
            start_minutes + duration_minutes
        )

        opening = target_act.get(
            "opening_time",
            "09:00",
        )

        closing = target_act.get(
            "closing_time",
            "19:00",
        )

        if hours_ok:
            feasibility = "The activity fits the operating-hours check."
        else:
            feasibility = (
                "The activity may not fit the operating-hours "
                "constraint at the proposed time."
            )

        lines = [
            (
                f"### Schedule Feasibility: "
                f"{target_act.get('name', 'Activity')}"
            ),
            "",
            f"- **Operating Hours**: {opening} to {closing}",
            f"- **Operating-hours Check**: {feasibility}",
            f"- **Estimated Duration**: {duration_minutes} minutes",
            (
                f"- **Estimated Cost**: "
                f"{target_act.get('estimated_cost', 0)} "
                f"INR per person"
            ),
            (
                f"- **Proposed Slot**: "
                f"{_minutes_to_time(start_minutes)} - "
                f"{_minutes_to_time(end_minutes)}"
            ),
            "- **Transit Buffer**: approximately 20 minutes",
            (
                f"- **Current Day 1 Activities**: "
                f"{len(day_items)}"
            ),
        ]

        return {
            "message": "\n".join(lines),
            "suggestions": [
                (
                    f"Add {target_act.get('name', 'this activity')} "
                    "to today's schedule"
                ),
                "Show route map",
                "Keep schedule as is",
            ],
        }

    # ------------------------------------------------------------------
    # PROXIMITY QUERY
    # ------------------------------------------------------------------

    def _handle_proximity_query(
        self,
        message: str,
        trip_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Answers:
        'Which activities are close to my hotel?'
        """

        hotel_booking = (
            db.query(BookingModel)
            .filter(
                BookingModel.trip_id == trip_id,
                BookingModel.booking_type == "Hotel",
            )
            .first()
        )

        hotel_name = (
            hotel_booking.title
            if hotel_booking
            else "Hôtel Saint-Germain Paris"
        )

        hotel_location = (
            hotel_booking.provider
            if hotel_booking
            else "Saint-Germain-des-Prés"
        )

        # Demo hotel coordinates.
        hotel_lat = 48.854167
        hotel_lon = 2.332778

        nearby_res = default_tool_registry.execute(
            "find_nearby_activities",
            latitude=hotel_lat,
            longitude=hotel_lon,
            radius_km=2.0,
            limit=4,
        )

        if nearby_res.get("success"):
            venues = (
                nearby_res.get("result", {})
                .get("activities", [])
            )
        else:
            venues = []

        lines = [
            (
                "Here are activities near your hotel "
                f"(**{hotel_name}**, {hotel_location}):"
            ),
            "",
        ]

        for venue in venues:

            distance = venue.get(
                "distance_km",
                0.5,
            )

            walking_minutes = max(
                5,
                round(distance * 12),
            )

            lines.append(
                f"- **{venue.get('name', 'Activity')}** "
                f"({distance:.1f} km away, "
                f"~{walking_minutes} min walk) - "
                f"{venue.get('category', 'Activity')}, "
                f"rating {venue.get('rating', 'N/A')}"
            )

        if not venues:
            lines.append(
                "No nearby activities were returned "
                "by the activity service."
            )

        lines.append(
            "\nTravelPilot can use these locations when "
            "optimizing your itinerary."
        )

        return {
            "message": "\n".join(lines),
            "suggestions": [
                (
                    f"Add "
                    f"{venues[0]['name'] if venues else 'a nearby venue'} "
                    "to my morning walk"
                ),
                "Directions from hotel",
                "Nearest coffee shops",
            ],
        }

    # ------------------------------------------------------------------
    # DISRUPTION SIMULATION
    # ------------------------------------------------------------------

    def _handle_disruption_simulation(
        self,
        message: str,
        trip_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Simulate a disruption without applying it.

        Example:
        'What if the Louvre is cancelled?'
        """

        target_name = "Musée du Louvre"

        message_lower = message.lower()

        for activity in dataset_service.all_activities:

            activity_name = str(
                activity.get("name", "")
            )

            words = [
                word
                for word in activity_name.lower().split()
                if len(word) > 4
            ]

            if (
                activity_name.lower()
                in message_lower
                or any(
                    word in message_lower
                    for word in words
                )
            ):
                target_name = activity_name
                break

        sim_res = (
            default_disruption_manager.simulate_disruption(
                trip_id=trip_id,
                disruption_type="activity_cancelled",
                title=target_name,
                db=db,
            )
        )

        if not sim_res:
            return {
                "message": (
                    "I couldn't simulate that disruption "
                    "right now."
                ),
                "suggestions": [
                    "View my itinerary",
                    "Check current budget",
                ],
            }

        recommended = sim_res.get(
            "recommended_alternative"
        )

        budget_impact = sim_res.get(
            "budget_impact",
            {},
        )

        spending_delta = float(
            budget_impact.get(
                "spending_delta",
                0.0,
            )
        )

        new_remaining = budget_impact.get(
            "new_remaining_budget"
        )

        currency = budget_impact.get(
            "currency",
            "INR",
        )

        affected_items = sim_res.get(
            "affected_items",
            [],
        )

        affected_name = (
            affected_items[0].get(
                "activity_name",
                target_name,
            )
            if affected_items
            else target_name
        )

        if spending_delta <= 0:
            budget_text = (
                f"{currency} "
                f"{abs(spending_delta):,.0f} saved"
            )
        else:
            budget_text = (
                f"{currency} "
                f"{spending_delta:,.0f} additional cost"
            )

        lines = [
            (
                f"If **{target_name}** is cancelled, "
                "here is how TravelPilot adapts your journey:"
            ),
            "",
            "### 1. Disruption Impact",
            f"- **Affected Item**: {affected_name}",
            f"- **Budget Impact**: {budget_text}",
        ]

        if new_remaining is not None:
            lines.append(
                f"- **Projected Remaining Budget**: "
                f"{currency} {float(new_remaining):,.0f}"
            )

        travel_impact = sim_res.get(
            "travel_impact",
            {},
        )

        lines.extend(
            [
                (
                    f"- **Travel Impact**: "
                    f"{travel_impact.get('distance_delta_km', 0.0)} "
                    "km route adjustment."
                ),
                "",
                "### 2. Recommended Alternative",
            ]
        )

        if recommended:

            lines.extend(
                [
                    (
                        f"- **{recommended.get('name', 'Alternative')}** "
                        f"({recommended.get('category', 'Activity')}, "
                        f"rating {recommended.get('rating', 'N/A')})"
                    ),
                    (
                        f"  {recommended.get('recommendation_reason', '')}"
                    ),
                    (
                        f"  **Cost**: "
                        f"{recommended.get('estimated_cost', 0):,.0f} INR"
                    ),
                    (
                        f"  **Transit**: "
                        f"~{recommended.get('estimated_transit_minutes', 15)} "
                        "minutes"
                    ),
                ]
            )

        lines.extend(
            [
                "",
                "### 3. Revised Schedule Preview",
                (
                    "- The affected slot can be replaced by "
                    f"**{recommended.get('name') if recommended else 'free time'}**."
                ),
                (
                    "- Downstream activities can be rescheduled "
                    "with updated travel buffers."
                ),
                "",
                (
                    "**Would you like me to apply these changes "
                    "to your live itinerary?**"
                ),
            ]
        )

        return {
            "action_type": "proposal",
            "message": "\n".join(lines),
            "suggestions": [
                "Apply it.",
                "Show other alternatives",
                "Keep original schedule",
            ],
        }

    # ------------------------------------------------------------------
    # CONFIRMATION / APPLY CHANGES
    # ------------------------------------------------------------------

    def _handle_confirmation(
        self,
        trip_id: str,
        db: Session,
        last_ai_msg: Optional[ChatMessageModel] = None,
    ) -> Dict[str, Any]:
        """
        Handles explicit confirmation such as:
        'Apply it.'
        """

        target_title = "Musée du Louvre"

        if (
            last_ai_msg
            and last_ai_msg.message
        ):
            match = re.search(
                r"If \*\*(.+?)\*\* is cancelled",
                last_ai_msg.message,
            )

            if match:
                target_title = match.group(1)

        replan_res = (
            default_disruption_manager.replan_and_apply(
                trip_id=trip_id,
                disruption_type="activity_cancelled",
                title=target_title,
                db=db,
            )
        )

        recommended = replan_res.get(
            "recommended_alternative"
        )

        recommended_name = (
            recommended.get("name")
            if recommended
            else "alternative activity"
        )

        updated_itinerary = replan_res.get(
            "updated_itinerary",
            [],
        )

        updated_spending = replan_res.get(
            "updated_spending"
        )

        lines = [
            (
                "Done! I applied the replanned itinerary "
                "and updated the live trip database."
            ),
            "",
            "### Why I changed this:",
            (
                "- The original activity was cancelled, "
                "so the schedule needed a replacement."
            ),
            (
                f"- **{recommended_name}** was selected "
                "as the replacement."
            ),
            (
                "- The replacement is checked against "
                "the available schedule and constraints."
            ),
            (
                "- TravelPilot re-optimized the affected "
                "part of the itinerary."
            ),
        ]

        if updated_spending is not None:
            lines.extend(
                [
                    "",
                    (
                        f"**Updated itinerary activities**: "
                        f"{len(updated_itinerary)}"
                    ),
                    (
                        f"**Reported itinerary spending**: "
                        f"INR {float(updated_spending):,.0f}"
                    ),
                ]
            )

        return {
            "action_type": "applied",
            "explanation": (
                "The itinerary was re-optimized after "
                "the confirmed disruption."
            ),
            "message": "\n".join(lines),
            "suggestions": [
                "View Day 1 schedule",
                "Check current budget",
                "Show walking route",
            ],
        }

    # ------------------------------------------------------------------
    # BUDGET QUERY
    # ------------------------------------------------------------------

    def _handle_budget_query(
        self,
        trip_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Answers:
        - How much have I spent?
        - How much budget do I have left?
        - What's my remaining budget?
        """

        data = self._get_budget_snapshot(
            trip_id,
            db,
        )

        currency = data["currency"]

        total_budget = data["total_budget"]
        total_spent = data["total_spent"]
        remaining = data["remaining_budget"]
        percentage = data["percentage_spent"]

        status = (
            data["spending_status"]
            .replace("_", " ")
            .title()
        )

        categories = data["categories"]

        if remaining >= 0:
            remaining_line = (
                f"- **Budget Remaining**: "
                f"{currency} {remaining:,.2f}"
            )
        else:
            remaining_line = (
                f"- **Budget Overrun**: "
                f"{currency} {abs(remaining):,.2f}"
            )

        lines = [
            "### 💰 Current Travel Budget",
            "",
            f"- **Total Budget**: {currency} {total_budget:,.2f}",
            (
                f"- **Committed Spending**: "
                f"{currency} {total_spent:,.2f}"
            ),
            remaining_line,
            f"- **Budget Used**: {percentage:.1f}%",
            f"- **Budget Status**: **{status}**",
            "",
            "### Category Breakdown",
            (
                f"- Accommodation: "
                f"{currency} "
                f"{categories['accommodation']:,.2f}"
            ),
            (
                f"- Activities: "
                f"{currency} "
                f"{categories['activities']:,.2f}"
            ),
            (
                f"- Transportation: "
                f"{currency} "
                f"{categories['transportation']:,.2f}"
            ),
            (
                f"- Food & Dining: "
                f"{currency} "
                f"{categories['food']:,.2f}"
            ),
            (
                f"- Miscellaneous: "
                f"{currency} "
                f"{categories['miscellaneous']:,.2f}"
            ),
        ]

        return {
            "message": "\n".join(lines),
            "suggestions": [
                "How can I save budget?",
                "Can I reduce my budget to 70000 INR?",
                "Show free activities nearby",
            ],
        }

    # ------------------------------------------------------------------
    # BUDGET ADJUSTMENT
    # ------------------------------------------------------------------

    def _handle_budget_adjustment(
        self,
        message: str,
        trip_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Handles requests such as:
        'Can I reduce my budget to 70000 INR?'
        """

        numbers = re.findall(
            r"\d+(?:\.\d+)?",
            message.replace(",", ""),
        )

        target_budget = (
            float(numbers[0])
            if numbers
            else 70000.0
        )

        trip = (
            db.query(TripModel)
            .filter(TripModel.id == trip_id)
            .first()
        )

        if not trip:
            return {
                "message": (
                    "I couldn't find the active trip."
                ),
                "suggestions": [
                    "Show trip overview",
                ],
            }

        current_budget = float(
            trip.budget or 0.0
        )

        budget_snapshot = (
            self._get_budget_snapshot(
                trip_id,
                db,
            )
        )

        current_spending = float(
            budget_snapshot["total_spent"]
        )

        currency = (
            trip.currency
            or budget_snapshot["currency"]
            or "INR"
        )

        feasible = (
            target_budget >= current_spending
        )

        delta = (
            current_budget - target_budget
        )

        if feasible:

            cushion = (
                target_budget
                - current_spending
            )

            lines = [
                (
                    f"Your current committed spending is "
                    f"**{currency} {current_spending:,.2f}**."
                ),
                "",
                (
                    f"A budget ceiling of "
                    f"**{currency} {target_budget:,.2f}** "
                    "would leave:"
                ),
                "",
                (
                    f"- **Remaining Cushion**: "
                    f"{currency} {cushion:,.2f}"
                ),
                (
                    f"- **Budget Change**: "
                    f"{currency} {delta:,.2f}"
                ),
                "",
                (
                    "This is a feasibility check only; "
                    "your official trip budget has not been changed."
                ),
            ]

        else:

            excess = (
                current_spending
                - target_budget
            )

            lines = [
                (
                    f"A budget ceiling of "
                    f"**{currency} {target_budget:,.2f}** "
                    "would be below your current committed spending."
                ),
                "",
                (
                    f"- **Current Committed Spending**: "
                    f"{currency} {current_spending:,.2f}"
                ),
                (
                    f"- **Amount to Rebalance**: "
                    f"{currency} {excess:,.2f}"
                ),
                "",
                (
                    "TravelPilot would need to simulate "
                    "lower-cost alternatives before applying "
                    "the reduced budget."
                ),
            ]

        return {
            "message": "\n".join(lines),
            "suggestions": [
                (
                    f"Update budget to "
                    f"{target_budget:,.0f} {currency}"
                ),
                "Simulate budget rebalancing",
                "Keep current budget",
            ],
        }

    # ------------------------------------------------------------------
    # INTEREST QUERY
    # ------------------------------------------------------------------

    def _handle_interest_query(
        self,
        message: str,
        trip_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Answers:
        'What activities match my photography interest?'
        """

        target_interest = "Photography"

        message_lower = message.lower()

        if "food" in message_lower:
            target_interest = "Food"

        elif (
            "museum" in message_lower
            or "museums" in message_lower
        ):
            target_interest = "Museums"

        elif (
            "history" in message_lower
            or "historic" in message_lower
        ):
            target_interest = "History"

        elif "nature" in message_lower:
            target_interest = "Nature"

        elif "shopping" in message_lower:
            target_interest = "Shopping"

        search_res = default_tool_registry.execute(
            "search_activities",
            query=target_interest,
            limit=4,
        )

        if search_res.get("success"):
            activities = (
                search_res.get("result", {})
                .get("activities", [])
            )
        else:
            activities = []

        lines = [
            (
                f"Here are activities matched to your "
                f"**{target_interest}** interest:"
            ),
            "",
        ]

        for activity in activities:

            cost = activity.get(
                "estimated_cost",
                0,
            )

            if cost == 0:
                cost_text = "Free"
            else:
                cost_text = f"{cost} INR"

            lines.append(
                f"- **{activity.get('name', 'Activity')}** "
                f"({activity.get('category', 'Activity')}, "
                f"rating {activity.get('rating', 'N/A')})"
            )

            description = str(
                activity.get(
                    "description",
                    "",
                )
            )

            if len(description) > 110:
                description = description[:110] + "..."

            lines.append(
                f"  {description} ({cost_text})"
            )

        if not activities:
            lines.append(
                "No matching activities were returned."
            )

        first_name = (
            activities[0].get(
                "name",
                target_interest,
            )
            if activities
            else target_interest
        )

        return {
            "message": "\n".join(lines),
            "suggestions": [
                f"Add {first_name} to Day 2",
                f"More {target_interest} spots",
                "View on map",
            ],
        }

    # ------------------------------------------------------------------
    # GENERAL QUERY
    # ------------------------------------------------------------------

    def _handle_general_query(
        self,
        message: str,
        trip_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Fallback for genuinely general travel questions.

        Important:
        Budget is obtained through _get_budget_snapshot()
        so this response does not display stale TripModel.spending.
        """

        trip = (
            db.query(TripModel)
            .filter(TripModel.id == trip_id)
            .first()
        )

        destination = (
            trip.destination
            if trip
            else "your destination"
        )

        budget_snapshot = (
            self._get_budget_snapshot(
                trip_id,
                db,
            )
        )

        currency = budget_snapshot["currency"]
        remaining = budget_snapshot[
            "remaining_budget"
        ]

        if remaining >= 0:
            budget_text = (
                f"{currency} {remaining:,.2f} "
                "remaining"
            )
        else:
            budget_text = (
                f"{currency} "
                f"{abs(remaining):,.2f} over budget"
            )

        return {
            "message": (
                f"Hello! I am your TravelPilot Co-pilot "
                f"monitoring your {destination} journey.\n\n"
                f"Your current budget status is "
                f"**{budget_text}**.\n\n"
                "How can I help you optimize your "
                "schedule or handle an unexpected "
                "travel change?"
            ),
            "suggestions": [
                "What should I do tomorrow morning?",
                "Which activities are close to my hotel?",
                "How much budget do I have left?",
                "How much have I spent?",
                "What if the Louvre is cancelled?",
            ],
        }


# ----------------------------------------------------------------------
# DEFAULT ASSISTANT INSTANCE
# ----------------------------------------------------------------------

default_travel_assistant = TravelAssistant()