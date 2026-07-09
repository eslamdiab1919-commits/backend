"""
app/history_builder.py

Builds a token-limited, pair-preserving conversation history list
from a list of messages loaded from Firestore (newest-first order).

Rules:
  - Never split a user/assistant pair.
  - Stop adding pairs once the running token estimate exceeds the budget.
  - Reverse the final list so messages are in chronological order
    (oldest first) as required by the OpenAI Responses API.

Token estimation: 1 token ≈ 4 characters (conservative approximation).
"""

from __future__ import annotations

from dataclasses import dataclass

import tiktoken
from cachetools import LRUCache

_encoding_cache = LRUCache(maxsize=4)

def _get_encoding(model: str = "gpt-4o") -> tiktoken.Encoding:
    if model not in _encoding_cache:
        try:
            _encoding_cache[model] = tiktoken.encoding_for_model(model)
        except KeyError:
            _encoding_cache[model] = tiktoken.get_encoding("cl100k_base")
    return _encoding_cache[model]

@dataclass
class HistoryMessage:
    role: str    # "user" | "assistant"
    content: str


def _estimate_tokens(text: str, model: str = "gpt-4o") -> int:
    """Accurate token estimate using tiktoken."""
    if not text:
        return 0
    encoding = _get_encoding(model)
    return len(encoding.encode(text))


def build_history(
    messages_desc: list[dict],
    token_budget: int,
) -> list[HistoryMessage]:
    """
    Convert a Firestore message list (descending) into a token-limited
    chronological history ready for the Responses API.

    Args:
        messages_desc: List of Firestore message dicts, newest first.
                       Each dict must have 'isUser' (bool) and 'content' (str).
        token_budget:  Max tokens to include in history.

    Returns:
        List of HistoryMessage in chronological order (oldest first).
    """
    if not messages_desc:
        return []

    # Work from newest to oldest, collecting complete pairs.
    # A pair is always (user, assistant) or kept together.
    pairs: list[tuple[HistoryMessage, HistoryMessage | None]] = []
    used_tokens = 0
    i = 0

    while i < len(messages_desc):
        msg = messages_desc[i]
        is_user = msg.get("isUser", True)
        content = str(msg.get("content", "")).strip()

        if not is_user:
            # Assistant message — look ahead for its user turn
            assistant_msg = HistoryMessage(role="assistant", content=content)
            assistant_tokens = _estimate_tokens(content)

            # Try to pair with the next message (should be the preceding user turn)
            if i + 1 < len(messages_desc):
                next_msg = messages_desc[i + 1]
                if next_msg.get("isUser", False):
                    user_content = str(next_msg.get("content", "")).strip()
                    user_msg = HistoryMessage(role="user", content=user_content)
                    pair_tokens = assistant_tokens + _estimate_tokens(user_content)

                    if used_tokens + pair_tokens > token_budget:
                        break  # Budget exceeded — stop here

                    pairs.append((user_msg, assistant_msg))
                    used_tokens += pair_tokens
                    i += 2
                    continue

            # Orphaned assistant message — include it alone if budget allows
            if used_tokens + assistant_tokens <= token_budget:
                pairs.append((assistant_msg, None))
                used_tokens += assistant_tokens
            i += 1

        else:
            # Standalone user message (no assistant reply yet)
            user_msg = HistoryMessage(role="user", content=content)
            token_cost = _estimate_tokens(content)
            if used_tokens + token_cost <= token_budget:
                pairs.append((user_msg, None))
                used_tokens += token_cost
            i += 1

    # Reverse to chronological order and flatten pairs
    chronological: list[HistoryMessage] = []
    for pair in reversed(pairs):
        msg_a, msg_b = pair
        chronological.append(msg_a)
        if msg_b is not None:
            chronological.append(msg_b)

    return chronological
