import httpx
import logging
from time import time
from typing import Dict, Any
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.memory.graph import get_similar_products
from backend.rag.rag import handle_rag
from backend.agents.planner_router import route_to_planner
from backend.core.llm_client import openai_chat
from backend.db.db import save_last_product


try:
    from backend.db.db import record_mcp_call
except Exception:
    from ..db import record_mcp_call

MCP_BASE = "http://localhost:8000/mcp" 

from sqlalchemy import text

def resolve_product_id_from_metadata(db, meta: dict):
    # Direct ID (if present)
    if meta.get("product_id"):
        return int(meta["product_id"])
    if meta.get("id"):
        return int(meta["id"])

    # Resolve via SKU
    sku = meta.get("sku")
    if sku:
        row = db.execute(
            text("SELECT id FROM products WHERE sku = :sku"),
            {"sku": sku},
        ).fetchone()
        if row:
            return int(row.id)

    return None


def execute_task(db: Optional[Session], task: Dict[str, Any], session_id: str, run_id: Optional[str] = None, lc_config: Optional[dict] = None,) -> Dict[str, Any]:
    name = task.get("task")
    args = task.get("args", {})
    start = time()
    # --------------------------------------------------
    # ENFORCE lc_config PROPAGATION
    # --------------------------------------------------
    if lc_config is None:
        lc_config = task.get("_lc_config")

    if lc_config is None:
        print(" lc_config is None — tracing will not work")

    task["_lc_config"] = lc_config

    print("🧪 lc_config passed to executor:", lc_config)
    # ─────────────────────────────────────────
    # GRAPH TOOL (Neo4j)
    # ─────────────────────────────────────────
    if name == "graph_similar_products":
        product_id = args.get("product_id")

        if not product_id:
            return {
                "task": name,
                "result": {"error": "product_id missing"},
            }
        duration_ms = int((time() - start) * 1000)
        graph_result = get_similar_products(product_id)
        if graph_result:
            save_last_product(db, session_id, product_id)
            print(f" Saved last_product_id from graph={product_id}")
        record_mcp_call(db, session_id, name, "neo4j", args, {"count": len(graph_result)}, "ok", duration_ms, run_id=run_id)

        return {
            "task": name,
            "result": graph_result,
        }
    elif name == "get_product_price":
            product_id = task.get("args", {}).get("product_id")

            product = db.execute(
                "SELECT name, price, currency FROM products WHERE id = :id",
                {"id": product_id}
            ).fetchone()

            if not product:
                return {
                    "task": name,
                    "status": "error",
                    "reply": "I could not find the product price."
                }

            reply = f"The price of {product.name} is ₹{int(product.price)}."
            record_mcp_call(db, session_id, "get_product_price", "postgres", args, {"message": "get_product_price"}, "ok", duration_ms, run_id=run_id)
            return {
                "task": name,
                "status": "ok",
                "reply": reply
            }
    try:
        if name == "authenticate_user":
            url = f"{MCP_BASE}/user_profile/{session_id}"
            resp = httpx.get(url, timeout=10.0)
            result = resp.json()
            status = "ok" if resp.status_code == 200 else "error"
            duration_ms = int((time() - start) * 1000)
            record_mcp_call(db, session_id, name, "get_user_profile", args, result, status, duration_ms, run_id=run_id)
            return {"task": name,"status": status, "result": result, "reply": None}  # no final reply
        elif name == "get_order_status":
            order_id = args.get("order_id")
            url = f"{MCP_BASE}/order_status/{order_id}"
            resp = httpx.get(url, timeout=10.0)
            result = resp.json()
            status = "ok" if resp.status_code == 200 else "error"
            duration_ms = int((time() - start) * 1000)
            record_mcp_call(db, session_id, name, "get_order_status", args, result, status, duration_ms, run_id=run_id)
            return {"task": name,"status": status, "result": result, "reply": None}  # no final reply
        elif name == "create_investigation":
            url = f"{MCP_BASE}/create_investigation"
            resp = httpx.post(url, json=args, timeout=10.0)
            result = resp.json()
            status = "ok" if resp.status_code == 200 else "error"
            duration_ms = int((time() - start) * 1000)
            record_mcp_call(db, session_id, name, "create_investigation", args, result, status, duration_ms, run_id=run_id)
            return {"task": name,"status": status, "result": result, "reply": None}  # no final reply
        elif name == "ask_for_order_id":
            duration_ms = int((time() - start) * 1000)
            record_mcp_call(db, session_id, name, "local", args, {"message": "ask_for_order_id"}, "ok", duration_ms, run_id=run_id)
            return {"task": name, "status": status,"result": {"message": "ask_for_order_id"}}
        elif name == "format_reply":
            formatted_text = args.get("text", "Here is the information you requested.")
            duration_ms = int((time() - start) * 1000)
            record_mcp_call(db, session_id, name, "local", args, {"message": "format_reply_noop"}, "ok", duration_ms, run_id=run_id)
            return {"task": name, "status": status,"reply": formatted_text, "result": {"message": "format_reply_noop"}}
        elif name == "rag_query":
            query = task.get("args", {}).get("query")
            original_query = task.get("args", {}).get("original_query", query)

            if not query:
                return {
                    "task": name,
                    "status": "error",
                    "reply": "Empty RAG query",
                    "sources": [],
                }

            # Run RAG
            rag_result = handle_rag(
                query=query,
                session_id=session_id,
                lc_config=lc_config,
            )

            duration_ms = int((time() - start) * 1000)
            sources = rag_result.get("sources", [])
            record_mcp_call(db=db,session_id=session_id,name="rag_query",tool="vector_search",args={"query": query},result={"source_count": len(rag_result.get("sources", []))},status="ok",duration_ms=duration_ms,run_id=run_id,)

            # Build final reply
            context = rag_result.get("reply") or ""
            # ----------------------------------
            # FINAL LLM CALL (FOR HELICONE)
            # ----------------------------------

            completion = openai_chat(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an ecommerce assistant. Answer using the provided context."
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion:\n{original_query}"
                    },
                ],
                session_id=session_id,
            )

            reply = completion.choices[0].message.content

            return {
                "task": name,
                "status": "ok",
                "reply": reply,
                "sources": sources,
            }
        elif name == "agent":
            transcript = args.get("transcript", "")
            if transcript is None:
                raise ValueError("Agent task requires transcript")
            # Route to planner logic
            plan = route_to_planner(transcript,session_id,db,)
            print(" AGENT PLAN:", plan)
            results = []
            final_reply = None
            sources = []

            for subtask in plan:
                res = execute_task(db, subtask, session_id, run_id=run_id, lc_config=lc_config,)
                results.append(res)
                print(" SUBTASK RESULT:", subtask["task"], res)
                if isinstance(res, dict):
                    if res.get("reply"):
                        final_reply = res["reply"]
                    if res.get("sources"):
                        sources.extend(res["sources"])
            # --------------------------------------------------
            # GLOBAL MEMORY SAVE (FINAL SAFETY NET)
            # --------------------------------------------------
            try:
                if sources:
                    meta = sources[0].get("metadata", {})
                    product_id = resolve_product_id_from_metadata(db, meta)
                    if product_id:
                        save_last_product(db, session_id, product_id)
                        print(f" [GLOBAL] Saved last_product_id={product_id}")
            except Exception as e:
                print(" Memory save skipped:", e)

            return {
                "reply": final_reply or "I don't know",
                "sources": sources,
                "actions": results
            }
        else:
            duration_ms = int((time() - start) * 1000)
            record_mcp_call(db, session_id, name, "unknown", args, {"error": "unknown task"}, "error", duration_ms, run_id=run_id)
            return {
                "task": name,
                "result": {
                "error": f"Unknown task: {name}",
                "needs_human": True
    }
}

    except Exception as e:
        duration_ms = int((time() - start) * 1000)
        try:
            record_mcp_call(db, session_id, name or "unknown", "exception", args, {"error": str(e)}, "error", duration_ms, run_id=run_id)
        except Exception:
            logging.exception("Failed to write mcp_call")
        logging.exception("Executor error")
        return {"task": name, "result": {"error": str(e)}}