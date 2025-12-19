from typing import List, Dict
import re

# -----------------------------
# Helpers
# -----------------------------

def normalize_text(t: str) -> str:
    return (
        t.lower()
         .replace("?", "")
         .replace(".", "")
         .replace("-", "")
         .replace("on", "ord")   # fixes "order on 0-0-2"
    )

def extract_order_id(text: str):
    t = text.lower().replace("-", "").replace(" ", "")
    m = re.search(r"(ord|order)?(\d{3,6})", t)
    if m:
        return f"ORD-{m.group(2)}"
    return None


# -----------------------------
# Main Planner
# -----------------------------

def plan_user_request(
    transcript: str,
    session_id: str,
    db,
) -> List[Dict]:
    """
    Rule-based planner that emits tool-level tasks.
    Stateless by design.
    """

    transcript_l = normalize_text(transcript)

    # --------------------------------------------------
    # ORDER TRACKING
    # --------------------------------------------------
    order_id = extract_order_id(transcript_l)
    if order_id:
        return [{
            "task": "order_query",
            "args": {"order_id": order_id},
        }]

    # --------------------------------------------------
    # HUMAN ESCALATION
    # --------------------------------------------------
    if any(k in transcript_l for k in ["human", "agent", "representative", "support"]):
        return [{
            "task": "escalation_query",
            "args": {},
        }]

    # --------------------------------------------------
    # POLICY
    # --------------------------------------------------
    if any(k in transcript_l for k in ["return policy", "refund", "returns"]):
        return [{
            "task": "policy_query",
            "args": {"query": transcript},
        }]

    # --------------------------------------------------
    # FAQ
    # --------------------------------------------------
    if any(k in transcript_l for k in ["delivery", "shipping"]):
        return [{
            "task": "faq_query",
            "args": {"query": transcript},
        }]

    # --------------------------------------------------
    # SIMILAR PRODUCTS
    # --------------------------------------------------
    if any(k in transcript_l for k in ["similar", "similar products", "alternatives", "compare"]):
        return [{
            "task": "graph_similar_products",
            "args": {},
        }]

    # --------------------------------------------------
    # DEFAULT → RAG
    # --------------------------------------------------
    return [{
        "task": "rag_query",
        "args": {
            "query": transcript,
        },
    }]
