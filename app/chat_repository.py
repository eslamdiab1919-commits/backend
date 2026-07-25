"""
app/chat_repository.py

Firestore read/write operations for chat messages and sessions.

Uses the async Firestore client to avoid blocking the event loop or thread pool exhaustion.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from firebase_admin import firestore_async
from google.cloud import firestore

from .config import get_config

logger = logging.getLogger(__name__)


def _db():
    """Return a Firestore async client."""
    return firestore_async.client()


# ---------------------------------------------------------------------------
# Message loading
# ---------------------------------------------------------------------------

async def load_recent_messages(
    uid: str,
    session_id: str,
    max_docs: int,
) -> list[dict]:
    """
    Load up to `max_docs` most-recent messages from Firestore,
    returned in descending order (newest first).
    """
    db = _db()
    
    query = (
        db.collection("users")
        .document(uid)
        .collection("chats")
        .document(session_id)
        .collection("messages")
        .order_by("createdAt", direction=firestore.Query.DESCENDING)
        .limit(max_docs)
    )
    
    snapshot = await query.get()
    return [doc.to_dict() for doc in snapshot]


# ---------------------------------------------------------------------------
# Message writing
# ---------------------------------------------------------------------------

async def save_user_message(
    uid: str,
    session_id: str,
    content: str,
    correlation_id: str | None = None,
) -> str:
    """
    Save the user's message to Firestore using a batch write.
    Returns the new document ID.
    """
    db = _db()
    batch = db.batch()
    
    msg_ref = (
        db.collection("users")
        .document(uid)
        .collection("chats")
        .document(session_id)
        .collection("messages")
        .document()
    )
    
    msg_data = {
        "content": content,
        "isUser": True,
        "createdAt": firestore.SERVER_TIMESTAMP,
    }
    if correlation_id:
        msg_data["client_message_id"] = correlation_id
        
    batch.set(msg_ref, msg_data)

    session_ref = (
        db.collection("users")
        .document(uid)
        .collection("chats")
        .document(session_id)
    )
    batch.set(session_ref, {"lastMessageAt": firestore.SERVER_TIMESTAMP}, merge=True)
    # Denormalize the activity marker on the user document so the dashboard
    # can page recent users without scanning every chat subcollection.
    batch.set(
        db.collection("users").document(uid),
        {
            "lastMessageAt": firestore.SERVER_TIMESTAMP,
            "lastChatId": session_id,
        },
        merge=True,
    )

    await batch.commit()
    return msg_ref.id


async def save_assistant_message(
    uid: str,
    session_id: str,
    content: str,
    citations: list[dict],
) -> None:
    """Save the assistant's response to Firestore using a batch write."""
    db = _db()
    batch = db.batch()
    
    msg_ref = (
        db.collection("users")
        .document(uid)
        .collection("chats")
        .document(session_id)
        .collection("messages")
        .document()
    )
    batch.set(msg_ref, {
        "content": content,
        "isUser": False,
        "citations": citations,
        "createdAt": firestore.SERVER_TIMESTAMP,
    })

    session_ref = (
        db.collection("users")
        .document(uid)
        .collection("chats")
        .document(session_id)
    )
    batch.set(session_ref, {"lastMessageAt": firestore.SERVER_TIMESTAMP}, merge=True)
    batch.set(
        db.collection("users").document(uid),
        {
            "lastMessageAt": firestore.SERVER_TIMESTAMP,
            "lastChatId": session_id,
        },
        merge=True,
    )

    await batch.commit()
