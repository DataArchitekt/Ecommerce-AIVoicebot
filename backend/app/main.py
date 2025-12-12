# backend/app/main.py
import os
import re
import time
import json
import traceback
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Load backend/.env if present
ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
if ENV.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV)

# Try to import project modules using both import styles
try:
    # prefer explicit backend package import when running from repo root
    from backend.app.db import init_db, get_history, save_history, get_product_by_id
    from backend.app.mcp_server import get_order_status as mcp_get_order_status
    from backend.app.rag import get_retriever
except Exception:
    # fallback when running with backend on PYTHONPATH as top-level package "app"
    try:
        from app.db import init_db, get_history, save_history, get_product_by_id
        from app.mcp_server import get_order_status as mcp_get_order_status
        from app.rag import get_retriever
    except Exception:
        # graceful placeholders if imports fail (keeps server up for other endpoints)
        init_db = lambda: None
        get_history = lambda session_id: []
        save_history = lambda session_id, history: None
        get_product_by_id = lambda pid: None
        mcp_get_order_status = lambda order_id: {"order_id": order_id, "status": "UNKNOWN", "eta": None}
        get_retriever = None

# Chain builder import (LangChain wiring)
try:
    from agents.langchain_prompts import build_chain
except Exception:
    try:
        from backend.agents.langchain_prompts import build_chain
    except Exception:
        build_chain = None

app = FastAPI(title="Ecommerce Voicebot Day-2 (Hybrid LLM)")

# Globals to hold retriever & chain
retriever = None
chain = None

@app.on_event("startup")
def startup_event():
    global retriever, chain
    # initialize DB (if configured)
    try:
        init_db()
    except Exception as e:
        print("DB init failed:", e)

    # Try to eagerly initialize retriever + chain; if it fails we lazily build later
    try:
        if get_retriever:
            retriever = get_retriever()
        if retriever and build_chain:
            chain = build_chain(retriever)
            print("RAG chain initialized on startup.")
        else:
            print("RAG chain not initialized on startup (missing retriever or build_chain).")
    except Exception:
        print("Warning: chain init failed on startup.")
        traceback.print_exc()
        retriever = None
        chain = None

@app.get("/health")
def health():
    return {"status": "ok", "time": int(time.time())}

class AgentRequest(BaseModel):
    transcript: str
    session_id: str

def parse_action_from_text(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    m = re.search(r"\[\[ACTION\]\](\{.*?\})\[\[/ACTION\]\]", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None

# Structured intent detection helpers
def detect_order_id(text: str) -> Optional[str]:
    m = re.search(r"\border\s*(?:id\s*)?[:#]?\s*(\d+)\b", text, re.I)
    if m:
        return m.group(1)
    return None

def detect_product_id(text: str) -> Optional[int]:
    m = re.search(r"\bproduct\s+(?:id\s*)?[:#]?\s*(\d+)\b", text, re.I)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None

@app.post("/agent/handle")
async def agent_handle(req: AgentRequest):
    """
    Accepts: { transcript: str, session_id: str }
    Returns: { reply: str, sources: [{page_content, metadata}], actions: [{name,args,...}] }
    """
    global retriever, chain

    if not req.transcript:
        raise HTTPException(status_code=400, detail="transcript required")

    # Load/save conversation history convenience
    try:
        history = get_history(req.session_id) or []
    except Exception:
        history = []

    # 1) Structured intent: ORDER (exact)
    order_id = detect_order_id(req.transcript)
    if order_id:
        # Call MCP stub (immediate deterministic path)
        try:
            mcp_result = mcp_get_order_status(order_id)
        except Exception as e:
            mcp_result = {"error": str(e)}
        reply = f"Order {order_id} status: {mcp_result.get('status', 'UNKNOWN')}. ETA: {mcp_result.get('eta')}"
        # persist history
        try:
            history.append({"role":"user","text":req.transcript})
            history.append({"role":"assistant","text":reply})
            save_history(req.session_id, history)
        except Exception:
            pass
        return {
            "reply": reply,
            "sources": [],
            "actions": [{"name":"get_order_status","args":{"order_id":order_id},"result":mcp_result}]
        }

    # 2) Structured intent: PRODUCT ID (exact)
    prod_id = detect_product_id(req.transcript)
    if prod_id is not None:
        try:
            prod = get_product_by_id(prod_id)
        except Exception:
            prod = None
        if prod:
            reply = f"{prod.get('name')} (SKU: {prod.get('sku')}): {prod.get('description')}. Price: {prod.get('price')} {prod.get('currency')}."
            try:
                history.append({"role":"user","text":req.transcript})
                history.append({"role":"assistant","text":reply})
                save_history(req.session_id, history)
            except Exception:
                pass
            return {
                "reply": reply,
                "sources": [{"page_content": str(prod), "metadata": {"table":"products","id":prod_id}}],
                "actions": []
            }
        # If product not found, continue to RAG fallback

    # 3) Ensure chain exists (lazy init)
    if chain is None:
        try:
            if get_retriever and build_chain:
                retriever = get_retriever()
                chain = build_chain(retriever)
                print("DEBUG: chain lazily initialized inside agent_handle.")
            else:
                print("DEBUG: get_retriever or build_chain unavailable.")
        except Exception as e:
            # print traceback in server logs and return a useful reply
            traceback.print_exc()
            reply = f"LLM init failed: {type(e).__name__}: {str(e)[:200]}"
            # save minimal history
            try:
                history.append({"role":"user","text":req.transcript})
                history.append({"role":"assistant","text":reply})
                save_history(req.session_id, history)
            except Exception:
                pass
            return {"reply": reply, "sources": [], "actions": []}

    # 4) If chain still missing, respond gracefully
    if chain is None:
        reply = "Agent not available (LLM not initialized)."
        try:
            history.append({"role":"user","text":req.transcript})
            history.append({"role":"assistant","text":reply})
            save_history(req.session_id, history)
        except Exception:
            pass
        return {"reply": reply, "sources": [], "actions": []}

    # 5) Prepare chat history for ConversationalRetrievalChain API (list of (user, assistant))
    formatted_history = []
    user_buf = None
    for item in history:
        r = item.get("role"); t = item.get("text")
        if r == "user":
            user_buf = t
        elif r == "assistant" and user_buf:
            formatted_history.append((user_buf, t))
            user_buf = None

    # 6) Run the chain
    try:
        result = chain({"question": req.transcript, "chat_history": formatted_history})
    except Exception as e:
        # fallback to older chain.run() shape if necessary
        try:
            result_text = chain.run(req.transcript)
            result = {"answer": result_text, "source_documents": []}
        except Exception as e2:
            traceback.print_exc()
            reply = f"LLM error: {type(e2).__name__}: {str(e2)[:200]}"
            try:
                history.append({"role":"user","text":req.transcript})
                history.append({"role":"assistant","text":reply})
                save_history(req.session_id, history)
            except Exception:
                pass
            return {"reply": reply, "sources": [], "actions": []}

    # 7) Normalize chain result
    reply_text = result.get("answer") or result.get("response") or result.get("output_text") or ""
    source_docs = []
    for d in result.get("source_documents", []):
        try:
            source_docs.append({"page_content": d.page_content, "metadata": getattr(d, "metadata", {})})
        except Exception:
            try:
                source_docs.append(dict(d))
            except Exception:
                source_docs.append({"page_content": str(d)})

    # 8) Parse actions embedded in LLM reply (if any) and call MCP
    action = parse_action_from_text(reply_text)
    actions = []
    if action:
        actions.append(action)
        if action.get("name") == "get_order_status":
            order_id_arg = action.get("args", {}).get("order_id")
            try:
                actions[0]["result"] = mcp_get_order_status(order_id_arg)
            except Exception as e:
                actions[0]["error"] = str(e)

    # 9) Save updated history
    try:
        history.append({"role":"user","text":req.transcript})
        history.append({"role":"assistant","text":reply_text})
        save_history(req.session_id, history)
    except Exception:
        pass

    return {"reply": reply_text, "sources": source_docs, "actions": actions}
