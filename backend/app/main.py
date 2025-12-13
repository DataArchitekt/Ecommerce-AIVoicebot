# backend/app/main.py
import os
import uuid
import time
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────
# ENV LOADING (must happen before tracer creation)
# ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# Enforce LangSmith defaults (Change 1 prerequisite)
os.environ.setdefault("LANGSMITH_TRACING", "true")
os.environ.setdefault("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

# ─────────────────────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────────────────────
app = FastAPI(title="Ecommerce Voicebot (Traced)")

# ─────────────────────────────────────────────────────────────
# Imports from project
# ─────────────────────────────────────────────────────────────
from backend.app.agents.planner import plan_track_order
from backend.app.agents.executor import execute_task
from backend.app.agents.evaluator import simple_evaluate
from backend.app.agents.trace_helpers import (
    make_langchain_tracer,
    runnable_config_for_tracer,
)

from backend.app.db import (
    get_history,
    save_history,
    record_mcp_call,
)

from backend.app.database import SessionLocal
from backend.app.mcp_server import get_order_status

from backend.app.agents.langchain_prompts import build_chain
from backend.app.rag import get_retriever

from langchain_core.runnables import RunnableLambda

# ─────────────────────────────────────────────────────────────
# Global chain (lazy init)
# ─────────────────────────────────────────────────────────────
retriever = None
chain = None

@app.on_event("startup")
def startup():
    global retriever, chain
    try:
        retriever = get_retriever()
        chain = build_chain(retriever)
        print("✅ RAG chain initialized")
    except Exception:
        traceback.print_exc()
        print("⚠️ Failed to initialize RAG chain")

# ─────────────────────────────────────────────────────────────
# Request model
# ─────────────────────────────────────────────────────────────
class AgentRequest(BaseModel):
    transcript: str
    session_id: str

# ─────────────────────────────────────────────────────────────
# CHANGE 2: Force at least one traced LangChain call per request
# ─────────────────────────────────────────────────────────────
def force_trace_ping(tracer, run_name: str):
    """
    Guarantees a LangChain invocation so LangSmith always records a run,
    even if we exit early (order-id/product-id shortcut paths).
    """
    if tracer is None:
        return

    ping = RunnableLambda(lambda x: "trace_ping")
    try:
        ping.invoke(
            {"ping": True},
            config=runnable_config_for_tracer(
                tracer,
                run_name=f"{run_name}_ping"
            )
        )
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────
# Main agent endpoint
# ─────────────────────────────────────────────────────────────
@app.post("/agent/handle")
def agent_handle(req: AgentRequest):
    if not req.transcript:
        raise HTTPException(status_code=400, detail="transcript required")

    # ─────────────────────────────────────────────────────────
    # CHANGE 4: Single tracer per request
    # ─────────────────────────────────────────────────────────
    run_id = str(uuid.uuid4())
    run_name = f"session_{req.session_id}_{run_id[:8]}"

    tracer = None
    config = {}
    try:
        tracer = make_langchain_tracer(
            project_name=os.getenv("LANGSMITH_PROJECT")
        )
        config = runnable_config_for_tracer(tracer, run_name=run_name)
        print(f"🧭 LangSmith run_name = {run_name}")
    except Exception as e:
        print("⚠️ Tracer disabled:", e)

    # Helper to safely record custom spans
    def trace_record(name: str, payload: Dict[str, Any]):
        if tracer is None:
            return
        try:
            tracer.record(name, payload)
        except Exception:
            pass

    # Load conversation history
    history = get_history(req.session_id) or []

    # ─────────────────────────────────────────────────────────
    # EARLY PATH 1 — Order ID detected
    # ─────────────────────────────────────────────────────────
    if "order" in req.transcript.lower():
        try:
            order_id = req.transcript.split()[-1]
            order = jsonable_encoder(get_order_status(order_id))
            reply = f"Order {order_id} is currently {order.get('status')}"

            force_trace_ping(tracer, run_name)

            history.extend([
                {"role": "user", "text": req.transcript},
                {"role": "assistant", "text": reply},
            ])
            save_history(req.session_id, history)

            return {
                "reply": reply,
                "sources": [],
                "actions": [{"name": "get_order_status", "args": {"order_id": order_id}}],
            }
        except Exception:
            pass  # fall through to agent flow

    # ─────────────────────────────────────────────────────────
    # PLANNER
    # ─────────────────────────────────────────────────────────
    plan = plan_track_order(req.transcript, req.session_id) or []
    trace_record("planner_output", {"plan": plan})

    # ─────────────────────────────────────────────────────────
    # EXECUTOR
    # ─────────────────────────────────────────────────────────
    db = SessionLocal()
    executor_results = []

    for task in plan:
        try:
            result = execute_task(db, task, req.session_id, run_id=run_id)
        except Exception as e:
            result = {"task": task.get("task"), "result": {"error": str(e)}}

        executor_results.append(result)
        trace_record("executor_call", jsonable_encoder(result))

    # ─────────────────────────────────────────────────────────
    # EVALUATOR
    # ─────────────────────────────────────────────────────────
    evaluation = simple_evaluate(executor_results)
    trace_record("evaluation", evaluation)

    # ─────────────────────────────────────────────────────────
    # CHANGE 3: ONLY invoke LangChain via `.invoke(..., config)`
    # ─────────────────────────────────────────────────────────
    if chain is None:
        force_trace_ping(tracer, run_name)
        return {"reply": "LLM unavailable", "sources": [], "actions": []}

    formatted_history = [
        (h1["text"], h2["text"])
        for h1, h2 in zip(history[::2], history[1::2])
        if h1["role"] == "user" and h2["role"] == "assistant"
    ]

    result = chain.invoke(
        {
            "question": req.transcript,
            "chat_history": formatted_history,
            "mcp_results": executor_results,
        },
        config=config,
    )

    reply_text = result.get("answer") or ""
    sources = result.get("source_documents", [])

    trace_record("final_reply", {"reply": reply_text})

    history.extend([
        {"role": "user", "text": req.transcript},
        {"role": "assistant", "text": reply_text},
    ])
    save_history(req.session_id, history)

    db.close()

    return {
        "reply": reply_text,
        "sources": sources,
        "actions": executor_results,
    }
