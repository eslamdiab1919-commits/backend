import json
import time
import asyncio
from typing import Dict, Any

from app.responses_api import stream_response
from app.prompts import get_system_prompt
from app.history_builder import _estimate_tokens
from app.openai_client import get_openai_client
from app.services.query_router import should_use_file_search
from app.config import get_config

async def evaluate_query(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs a single evaluation query against the RAG pipeline.
    Calculates TTFT, latency, tokens, cost, and uses gpt-4o-mini as a judge.
    """
    query = item["query"]
    expected = item["expected_behavior"]
    
    start_time = time.perf_counter()
    ttft = None
    
    messages = [{"role": "user", "content": query}]
    system_prompt = get_system_prompt()
    
    output_text = []
    citations = []
    
    config = get_config()
    tools = []
    if should_use_file_search(query):
        tools.append({
            "type": "file_search",
            "vector_store_ids": [config.OPENAI_VECTOR_STORE_ID],
        })
    
    try:
        async for chunk in stream_response(messages, system_prompt, ):
            if ttft is None:
                ttft = time.perf_counter() - start_time
                
            if chunk.startswith("data: "):
                raw = chunk[6:].strip()
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                    if payload.get("type") == "chunk":
                        output_text.append(payload.get("content", ""))
                    elif payload.get("type") == "done":
                        citations.extend(payload.get("citations", []))
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        return {"id": item["id"], "error": str(e)}
        
    total_time = time.perf_counter() - start_time
    full_text = "".join(output_text).strip()
    
    # Calculate tokens & estimated cost for gpt-4o-mini
    # $0.150 / 1M input, $0.600 / 1M output
    in_tokens = _estimate_tokens(system_prompt + query, "gpt-4o-mini")
    out_tokens = _estimate_tokens(full_text, "gpt-4o-mini")
    cost = (in_tokens / 1_000_000 * 0.150) + (out_tokens / 1_000_000 * 0.600)
    
    # LLM-as-a-judge for Answer Quality
    client = get_openai_client()
    judge_prompt = f"""Evaluate the following response to the user query for quality and groundedness.
User Query: {query}
Expected Behavior: {json.dumps(expected, ensure_ascii=False)}
Assistant Response: {full_text}

Rules:
- If 'must_refuse' is true, check if the assistant politely refused to answer ("عذراً، لا أملك معلومات كافية...").
- If 'eval_rule' exists, verify that condition.
- Evaluate if the response is helpful, clear, and doesn't invent facts.
Output ONLY 'PASS' or 'FAIL' followed by a short 1 sentence reason.
Example: PASS - The assistant correctly answered and provided relevant information.
"""
    try:
        judge_res = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": judge_prompt}],
            max_tokens=100,
            temperature=0
        )
        judge_output = judge_res.choices[0].message.content.strip()
    except Exception as e:
        judge_output = f"FAIL - Judge Error: {str(e)}"
        
    passed = judge_output.startswith("PASS")
    
    # Check citations
    has_citations = len(citations) > 0
    if expected.get("requires_citation") and not has_citations:
        passed = False
        judge_output += " (Failed: Missing required citations)"
        
    return {
        "id": item["id"],
        "category": item["category"],
        "query": query,
        "latency_sec": round(total_time, 2),
        "ttft_sec": round(ttft or total_time, 2),
        "in_tokens": in_tokens,
        "out_tokens": out_tokens,
        "cost_usd": cost,
        "has_citations": has_citations,
        "passed": passed,
        "judge_reason": judge_output,
        "response": full_text
    }
