"""
app/missed_query_repository.py

Firestore operations for managing missed query analytics and deduplication.
"""

from __future__ import annotations

import logging
from google.cloud import firestore
from firebase_admin import firestore_async

logger = logging.getLogger(__name__)


def _db():
    return firestore_async.client()


async def upsert_missed_query(
    query_id: str,
    original_query: str,
    reason: str,
    category: str,
    model: str,
    chat_id: str | None,
) -> None:
    """
    Upserts a missed query into the dashboard collection.
    Uses query_id (SHA-256 hash) for deterministic deduplication.
    Increments frequency if it exists, creates with metadata if new.
    """
    db = _db()
    doc_ref = db.collection("missed_queries").document(query_id)

    try:
        doc = await doc_ref.get()
        if doc.exists:
            # Update existing entry
            update_data = {
                "frequency": firestore.Increment(1),
                "lastAskedAt": firestore.SERVER_TIMESTAMP,
            }
            if chat_id:
                update_data["chatIds"] = firestore.ArrayUnion([chat_id])
                
            await doc_ref.update(update_data)
            logger.info("Incremented frequency for missed query: %s", query_id)
        else:
            # Create new entry
            await doc_ref.set({
                "query": original_query,
                "canonicalQuestion": None,  # For future semantic clustering
                "frequency": 1,
                "firstAskedAt": firestore.SERVER_TIMESTAMP,
                "lastAskedAt": firestore.SERVER_TIMESTAMP,
                "reason": reason,
                "category": category,
                "model": model,
                "status": "Pending",
                "resolved": False,
                "resolvedAt": None,
                "resolvedBy": None,
                "resolutionNote": None,
                "chatIds": [chat_id] if chat_id else []
            })
            logger.info("Created new missed query tracking doc: %s", query_id)
            
    except Exception as e:
        logger.exception("Failed to upsert missed query to Firestore: %s", e)
