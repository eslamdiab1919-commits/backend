"""
app/services/query_router.py

Isolated component to decide if a user query requires Vector Store retrieval.
Designed to be conservative (prioritizes false positives over false negatives)
and evolvable into a lightweight intent classifier without changing core logic.
"""

def should_use_file_search(user_message: str) -> bool:
    """
    Determines if File Search is necessary for the given message.
    Returns True if retrieval might be needed, False if definitely not needed.
    """
    text = user_message.strip().lower()
    
    # 1. Conservative fallback: Any message longer than 3 words is assumed to need retrieval.
    # Students rarely ask complex academic questions in 3 words or less.
    words = text.split()
    if len(words) > 3:
        return True
        
    # 2. Minimal heuristic for very obvious conversational queries
    # Avoids a massive, unmaintainable regex list. Only captures the most absolute basics.
    casual_phrases = {
        "مرحبا", "أهلا", "هلا", "السلام عليكم", "شلونك", "كيفك",
        "شكرا", "يعطيك العافية", "مشكور", "شكراً",
        "hi", "hello", "thanks", "ok", "نعم", "لا"
    }
    
    # Check if the text matches or closely contains these phrases
    if text in casual_phrases or any(text == p for p in casual_phrases):
        return False
        
    # If in doubt, ALWAYS retrieve.
    return True
