"""
app/services/missed_query_service.py

Analyzes missed queries in the background and upserts them into Firestore.
"""

import hashlib
import json
import logging

from app.openai_client import get_openai_client
from app.missed_query_repository import upsert_missed_query

logger = logging.getLogger(__name__)

async def analyze_and_log_missed_query(
    query: str,
    chat_id: str | None,
    was_file_search_attempted: bool,
    model_used: str
) -> None:
    """
    Background task: Use an LLM to classify why the query was missed,
    hash it for deduplication, and store it in Firestore.
    """
    try:
        # 1. Deterministic ID based on normalized text
        normalized_query = query.strip().lower()
        query_id = hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()
        
        # 2. Fast classification call to gpt-4o-mini
        client = get_openai_client()
        
        system_prompt = """You are an AI analytics assistant for Kuwait University. 
Your job is to classify a user's query that the main AI was unable to answer.
Determine the most appropriate category and the likely reason the main AI could not answer it."""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Query: {query}"}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "missed_query_classification",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "enum": ["academic", "casual", "out_of_domain", "ambiguous"]
                            },
                            "reason": {
                                "type": "string",
                                "enum": ["No matching document", "Ambiguous question", "Out of university scope", "Prompt Injection"]
                            }
                        },
                        "required": ["category", "reason"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            },
            temperature=0.0
        )
        
        raw_result = response.choices[0].message.content
        result = json.loads(raw_result)
        
        category = result.get("category", "unknown")
        reason = result.get("reason", "Unknown reason")
        
        # Override reason if we didn't even attempt search
        if category == "academic" and not was_file_search_attempted:
            reason = "File search improperly skipped"
            
        # 3. Upsert to Firestore
        await upsert_missed_query(
            query_id=query_id,
            original_query=query,
            reason=reason,
            category=category,
            model=model_used,
            chat_id=chat_id
        )
        
    except Exception as e:
        logger.exception("Error in analyze_and_log_missed_query background task: %s", e)
