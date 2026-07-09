"""
app/openai_client.py

Provides a singleton async OpenAI client.
The async client allows non-blocking API calls inside FastAPI coroutines.
"""

from functools import lru_cache

from openai import AsyncOpenAI

from .config import get_config


@lru_cache(maxsize=1)
def get_openai_client() -> AsyncOpenAI:
    """Return a singleton async OpenAI client."""
    config = get_config()
    return AsyncOpenAI(
        api_key=config.OPENAI_API_KEY,
        timeout=config.OPENAI_TIMEOUT
    )
