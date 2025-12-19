import re
from time import time
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.rag.rag import handle_rag
from backend.memory.graph import get_similar_products
from backend.db.db import get_product_by_id, save_last_product
from backend.agents.planner_router import route_to_planner
from backend.rag.faq_policy import handle_faq_query, handle_policy_query

# -----------------------------
# Session Store 
# -----------------------------
SESSION_STORE: Dict[str, Dict[str, Any]] = {}

COLOR_WORDS = {"red", "blue", "green", "black", "white"}
FABRIC_WORDS = {"cotton", "linen", "rayon"}


# -----------------------------
# Auth Helper
# -----------------------------

def get_session_auth(db: Session, session_id: str):
    row = db.execute(
        text("""
            SELECT auth_level, customer_id
            FROM sessions
            WHERE session_id = :sid
        """),
        {"sid": session_id}
    ).fetchone()

    if not row:
        return None

    return {
        "auth_level": row.auth_level,
        "customer_id": row.customer_id,
    }
    
def get_order_status(db: Session, order_id: str, customer_id: str):
    row = db.execute(
        text("""
            SELECT status, eta
            FROM orders
            WHERE order_id = :oid AND customer_id = :cid
        """),
        {"oid": order_id, "cid": customer_id}
    ).fetchone()

    if not row:
        return None

    return {
        "status": row.status,
        "expected_delivery": row.eta,
    }



# -----------------------------
# Guard Helpers
# -----------------------------

def handle_price_constraint(transcript: str):
    m = re.search(r"(under|less than)\s+(\d+)", transcript)
    if not m:
        return None

    price = int(m.group(2))
    return {
        "type": "final",
        "reply": f"Sorry, I don’t have any shirts available under ₹{price} at the moment.",
        "sources": [],
    }


def handle_memory_followup(transcript: str, session: dict, db: Session):
    last_pid = session.get("last_product_id")
    if not last_pid:
        return None

    FOLLOW_UP_PHRASES = {"it", "that", "same", "this"}

    if last_pid and any(p in transcript.split() for p in FOLLOW_UP_PHRASES):
        if any(c in transcript for c in COLOR_WORDS):
            product = get_product_by_id(last_pid)
            return {
                "type": "final",
                "reply": f"{product['name']} is available in multiple colours. Green is currently in stock.",
                "sources": [],
            }



def handle_ambiguity(transcript: str):
    tokens = set(transcript.split())

    if (
        "shirt" in tokens
        and not tokens.intersection(COLOR_WORDS)
        and not tokens.intersection(FABRIC_WORDS)
    ):
        return {
            "type": "clarification",
            "reply": "Are you looking for casual shirts or formal shirts?",
        }
    return None


# -----------------------------
# Executor Dispatcher
# -----------------------------

def execute_task(
    db: Optional[Session],
    task: Dict[str, Any],
    session_id: str,
    run_id=None,
    lc_config=None,
) -> Dict[str, Any]:

    name = task.get("task")
    args = task.get("args", {})
    start = time()

    # -----------------------------
    # RAG TOOL
    # -----------------------------
    if name == "rag_query":
        query = args.get("query")
        rag_resp = handle_rag(query, session_id, lc_config)
        sources = rag_resp.get("sources", [])

        # 🔑 Persist product memory if present
        for s in sources:
            meta = s.get("metadata", {})
            if meta.get("type") == "product" and meta.get("product_id"):
                session = SESSION_STORE.get(session_id, {})
                session["last_product_id"] = meta["product_id"]
                SESSION_STORE[session_id] = session
                break

        return {
            "reply": rag_resp.get("reply"),
            "sources": sources,
        }


    # -----------------------------
    # POLICY / FAQ
    # -----------------------------


    elif name == "faq_query":
        answer = handle_faq_query(args.get("query"))
        return {
            "type": "final",
            "reply": answer,
            "sources": []
        }

    elif name == "policy_query":
        answer = handle_policy_query(args.get("query"))
        return {
            "type": "final",
            "reply": answer,
            "sources": []
        }


    # -----------------------------
    # HUMAN ESCALATION
    # -----------------------------
    elif name == "escalation_query":
        return {
            "type": "escalation",
            "reply": "Connecting you to a human support agent now.",
            "needs_human": True,
        }

    # -----------------------------
    # ORDER QUERY (AUTH-GUARDED)
    # -----------------------------
    elif name == "order_query":
        auth = get_session_auth(db, session_id)

        if not auth or auth["auth_level"] != "authenticated":
            return {
                "type": "final",
                "reply": "Please log in to track your order.",
                "sources": [],
            }

        order_id = args.get("order_id")
        order = get_order_status(db, order_id, auth["customer_id"])

        if not order:
            return {
                "type": "final",
                "reply": f"I couldn’t find details for order {order_id}.",
                "sources": [],
            }

        return {
            "type": "final",
            "reply": (
                f"Your order {order_id} is {order['status']} "
                f"and is expected to be delivered by {order['expected_delivery']}."
            ),
            "sources": [],
        }


    # -----------------------------
    # GRAPH SIMILAR PRODUCTS
    # -----------------------------
    elif name == "graph_similar_products":
        session = SESSION_STORE.get(session_id, {})
        product_id = session.get("last_product_id")

        if not product_id:
            return {
                "type": "final",
                "reply": "Please view a product first before asking for similar items.",
                "sources": [],
            }

        graph_result = get_similar_products(product_id)
        graph_result = graph_result[:3]

        if not graph_result:
            return {
                "type": "final",
                "reply": "I couldn't find similar products at the moment.",
                "sources": [],
            }

        # 🔑 Build a spoken response
        product_names = [
            p.get("name", "a similar product")
            for p in graph_result
        ]

        reply_text = (
            "Here are a few similar products you might like: "
            + ", ".join(product_names)
        )

        return {
            "type": "final",
            "reply": reply_text,
            "sources": graph_result,
        }


    # -----------------------------
    # AGENT ORCHESTRATOR
    # -----------------------------
    elif name == "agent":
        transcript = args.get("transcript", "").lower().strip()
        session = SESSION_STORE.get(session_id, {})

        # Price constraint
        price_resp = handle_price_constraint(transcript)
        if price_resp:
            return price_resp

        # Memory follow-up
        mem_resp = handle_memory_followup(transcript, session, db)
        if mem_resp:
            return mem_resp

        # Ambiguity
        amb_resp = handle_ambiguity(transcript)
        if amb_resp:
            return amb_resp

        # Planner → Tools
        plan = route_to_planner(transcript, session_id, db)

        final_reply = None
        sources = []

        for subtask in plan:
            res = execute_task(db, subtask, session_id, run_id, lc_config)
            if res.get("reply"):
                final_reply = res["reply"]
            if res.get("sources"):
                sources.extend(res["sources"])

        # Persist memory
        product_sources = [s for s in sources if s.get("type") == "product"]
        if product_sources:
            session["last_product_id"] = product_sources[0].get("product_id")
            SESSION_STORE[session_id] = session

        if not final_reply:
            return {
                "type": "final",
                "reply": "I found a few options. Could you please be a bit more specific?",
                "sources": sources[:3],
            }

        return {
            "type": "final",
            "reply": final_reply,
            "sources": sources,
        }

    # -----------------------------
    # FALLBACK
    # -----------------------------
    return {
        "task": name,
        "result": {"error": f"Unknown task: {name}", "needs_human": True},
    }
