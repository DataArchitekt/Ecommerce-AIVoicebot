import httpx
import logging
from time import time
from typing import Dict, Any
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.graph import get_similar_products
from backend.app.rag import handle_rag

# Adjust these imports/paths to fit your project
try:
    from backend.app.db import record_mcp_call  # as suggested earlier
except Exception:
    # fallback if db helper is in a different module
    from ..db import record_mcp_call  # relative import if package layout differs

MCP_BASE = "http://localhost:8000/mcp" 

def execute_task(db: Optional[Session], task: Dict[str, Any], session_id: str, run_id: Optional[str] = None) -> Dict[str, Any]:
    name = task.get("task")
    args = task.get("args", {})
    start = time()
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

        graph_result = get_similar_products(product_id)

        return {
            "task": name,
            "result": graph_result,
        }

    try:
        if name == "authenticate_user":
            url = f"{MCP_BASE}/user_profile/{session_id}"
            resp = httpx.get(url, timeout=10.0)
            result = resp.json()
            status = "ok" if resp.status_code == 200 else "error"
            duration_ms = int((time() - start) * 1000)
            record_mcp_call(db, session_id, name, "get_user_profile", args, result, status, duration_ms, run_id=run_id)
            return {"task": name,"status": status, "result": result, "reply": None}  # explicitly no final reply
        elif name == "get_order_status":
            order_id = args.get("order_id")
            url = f"{MCP_BASE}/order_status/{order_id}"
            resp = httpx.get(url, timeout=10.0)
            result = resp.json()
            status = "ok" if resp.status_code == 200 else "error"
            duration_ms = int((time() - start) * 1000)
            record_mcp_call(db, session_id, name, "get_order_status", args, result, status, duration_ms, run_id=run_id)
            return {"task": name,"status": status, "result": result, "reply": None}  # explicitly no final reply
        elif name == "create_investigation":
            url = f"{MCP_BASE}/create_investigation"
            resp = httpx.post(url, json=args, timeout=10.0)
            result = resp.json()
            status = "ok" if resp.status_code == 200 else "error"
            duration_ms = int((time() - start) * 1000)
            record_mcp_call(db, session_id, name, "create_investigation", args, result, status, duration_ms, run_id=run_id)
            return {"task": name,"status": status, "result": result, "reply": None}  # explicitly no final reply
        elif name == "ask_for_order_id":
            duration_ms = int((time() - start) * 1000)
            record_mcp_call(db, session_id, name, "local", args, {"message": "ask_for_order_id"}, "ok", duration_ms, run_id=run_id)
            return {"task": name, "status": status,"result": {"message": "ask_for_order_id"}}
        elif name == "format_reply":
            formatted_text = args.get("text", "Here is the information you requested.")
            # do nothing heavy here; final composition happens elsewhere
            duration_ms = int((time() - start) * 1000)
            record_mcp_call(db, session_id, name, "local", args, {"message": "format_reply_noop"}, "ok", duration_ms, run_id=run_id)
            return {"task": name, "status": status,"reply": formatted_text, "result": {"message": "format_reply_noop"}}
        elif name == "rag_query":
            query = task.get("args", {}).get("query")
            if not query:
                return {
                    "task": name,
                    "status": "error",
                    "reply": "Empty RAG query",
                    "sources": [],}
            rag_result = handle_rag(query=query, session_id=session_id)
            return {
                    "task": name,
                    "status": "ok",
                    "reply": rag_result.get("reply", ""),
                    "sources": rag_result.get("sources", []),}
        else:
            duration_ms = int((time() - start) * 1000)
            record_mcp_call(db, session_id, name, "unknown", args, {"error": "unknown task"}, "error", duration_ms, run_id=run_id)
            return {
                "task": name,
                "result": {
                "error": "unknown task",
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