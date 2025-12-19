import re
from typing import List, Dict
from backend.db.db import get_last_product_id
# ---------------------------
# Extractors
# ---------------------------

def extract_order_id(text: str):
    m = re.search(
        r"\b(?:order|order id|order#|order no\.?)[:\s#-]*([0-9]{3,})\b",
        text,
        re.I,
    )
    return m.group(1) if m else None


def extract_product_id(text: str):
    m = re.search(
        r"\b(?:product|product id|product#|sku)[:\s#-]*([0-9A-Za-z]{1,})\b",
        text,
        re.I,
    )
    return m.group(1) if m else None


# ---------------------------
# Query Normalization
# ---------------------------

def normalize_rag_query(transcript: str) -> str:
    """
    Convert conversational user query into retrieval-friendly form.
    """
    text = transcript.lower().strip()

    text = re.sub(
        r"^(tell me about|can you tell me about|what is|what are|show me)\s+",
        "",
        text,
    )

    text = re.sub(
        r"product\s+(\d+)",
        r"product \1 description ecommerce catalog",
        text,
    )

    return text


# ---------------------------
# Planner: Order Tracking
# ---------------------------

def plan_track_order(transcript: str, session_id: str) -> List[Dict]:
    tasks = []
    order_id = extract_order_id(transcript)

    if order_id:
        tasks.extend([
            {
                "task": "authenticate_user",
                "args": {"session_id": session_id},
            },
            {
                "task": "get_order_status",
                "args": {"order_id": order_id},
            },
            {
                "task": "format_reply",
            },
        ])

    return tasks


# ---------------------------
# Planner: General User Query
# ---------------------------

def plan_user_request(
    transcript: str,
    session_id: str,
    db,
) -> List[Dict]:
    """
    Planner decides which tools to invoke based on user intent
    """

    plan: List[Dict] = []
    transcript_l = transcript.lower()

    # --------------------------------------------------
    # PRICE INTENT
    # --------------------------------------------------
    if "price" in transcript_l:
        product_id = get_last_product_id(db, session_id)

        if product_id:
            print(f" Planner: price intent → memory hit ({product_id})")
            return [{
                "task": "get_product_price",
                "args": {"product_id": product_id},
            }]

        print("🧠 Planner: price intent but no memory → fallback to RAG")

    # --------------------------------------------------
    # SIMILAR / COMPARE INTENT
    # --------------------------------------------------
    if any(k in transcript_l for k in ["similar", "compare", "alternatives"]):
        product_id = get_last_product_id(db, session_id)

        if not product_id:
            product_id = extract_product_id(transcript)

        if product_id:
            print(f" Planner: similar intent → product_id={product_id}")
            plan.append({
                "task": "graph_similar_products",
                "args": {"product_id": product_id},
            })

    # --------------------------------------------------
    # DEFAULT RAG
    # --------------------------------------------------
    normalized_query = normalize_rag_query(transcript)

    plan.append({
        "task": "rag_query",
        "args": {
            "query": normalized_query,
            "original_query": transcript,
        },
    })

    return plan