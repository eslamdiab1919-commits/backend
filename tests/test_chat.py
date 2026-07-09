import pytest
import uuid
from pydantic import ValidationError
from app.routers.chat import ChatRequest

def test_chat_request_valid_uuid():
    valid_uuid = str(uuid.uuid4())
    req = ChatRequest(
        message="Hello",
        sessionId="session_123",
        client_message_id=valid_uuid
    )
    assert req.client_message_id == valid_uuid
    assert req.message == "Hello"

def test_chat_request_missing_uuid():
    # Should be valid (backward compatibility)
    req = ChatRequest(
        message="Hello",
        sessionId="session_123"
    )
    assert req.client_message_id is None

def test_chat_request_invalid_uuid():
    with pytest.raises(ValidationError) as exc_info:
        ChatRequest(
            message="Hello",
            sessionId="session_123",
            client_message_id="not-a-uuid"
        )
    assert "client_message_id must be a valid UUID string" in str(exc_info.value)
