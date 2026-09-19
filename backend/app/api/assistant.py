"""
TravelPilot API - Assistant Router
Connects the chat endpoint to TravelPilot's Conversational AI Assistant.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.agents.travel_assistant import default_travel_assistant
from app.database.session import get_db
from app.models.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatResponse,
)

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def chat_with_assistant(
    payload: ChatMessageRequest, db: Session = Depends(get_db)
):
    """
    Interact with TravelPilot's Conversational AI Assistant.
    Understands current trip state, calls tools, handles what-if disruption simulations,
    and supports confirmation flows before applying schedule mutations.
    """
    chat_result = default_travel_assistant.chat(
        message=payload.message,
        trip_id=payload.trip_id,
        db=db,
    )

    return ChatResponse(
        status=chat_result["status"],
        intent=chat_result.get("intent"),
        action_type=chat_result.get("action_type"),
        user_message=ChatMessageResponse(**chat_result["user_message"]),
        ai_response=ChatMessageResponse(**chat_result["ai_response"]),
    )
