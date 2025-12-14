import re
from typing import List, Dict

def extract_order_id(text: str):
    m = re.search(r"\b(?:order|order id|order#|order no\.?)[:\s#-]*([0-9]{3,})\b", text, re.I)
    return m.group(1) if m else None

def plan_track_order(transcript: str, session_id: str) -> List[Dict]:
    """
    Return ordered list of tasks (max 4). Each task: {"task": "...", "args": {...}}
    """


    tasks = []
    order_id = extract_order_id(transcript)

# -------------------------------------------------
# Conditional authentication (FIX)
# -------------------------------------------------

    # Order-related queries → authentication required
    if order_id:
        tasks.append({
            "task": "authenticate_user",
            "args": {"session_id": session_id}
        })
        tasks.append({
            "task": "get_order_status",
            "args": {"order_id": order_id}
        })

    # Knowledge / product queries → NO authentication
    else:
        tasks.append({
            "task": "rag_query",
            "args": {"query": transcript}
        })
        tasks.append({
            "task": "rag_query",
            "args": {"query": transcript}
        }
)

    # Always end with formatter
        tasks.append({
            "task": "format_reply"
        })

    return tasks

def plan_user_request(transcript: str, session_id: str):
    plan = []

    if "similar" in transcript.lower() or "compare" in transcript.lower():
        product_id = extract_product_id(transcript)
        if product_id:
            plan.append({
                "task": "graph_similar_products",
                "args": {"product_id": product_id}
            })

    # fallback to existing RAG
    plan.append({
        "task": "rag_answer",
        "args": {"query": transcript}
    })

    return plan

