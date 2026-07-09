"""
routers/chat.py

POST /chat
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from ..auth import verify_token
from ..services.chat_service import process_chat
from ..limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000, description="User message content")
    sessionId: str = Field(..., description="Unique session ID")
    systemContext: str | None = Field(None, max_length=1000, description="Optional extra system instructions")
    client_message_id: str | None = Field(None, description="Client-generated correlation ID")

    @field_validator("client_message_id")
    def validate_uuid(cls, v):
        if v is not None:
            import uuid
            try:
                uuid.UUID(str(v))
            except ValueError:
                raise ValueError("client_message_id must be a valid UUID string")
        return v



@router.post("/chat")
@limiter.limit("10/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    uid: str = Depends(verify_token),
):
    """
    Stream an AI response to the client as Server-Sent Events.
    """
    message = body.message.strip()
    session_id = body.sessionId.strip()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'message' cannot be empty.",
        )
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'sessionId' cannot be empty.",
        )

    # Use the service layer to process the chat
    stream = process_chat(
        uid=uid,
        session_id=session_id,
        message=message,
        system_context=body.systemContext,
        correlation_id=body.client_message_id,
    )

    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",   # Nginx: disable buffering
        },
    )
