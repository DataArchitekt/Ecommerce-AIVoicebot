# backend/app/main.py
import os
import uuid
import time
import traceback
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from dotenv import load_dotenv

from fastapi import WebSocket
from app.tts_adapter import TTSAdapter
from app.ws_audio_out import stream_wav_over_ws
from app.stt_file import router as stt_router

from fastapi.middleware.cors import CORSMiddleware



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
app.include_router(stt_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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

ESCALATION_VOICE_PROMPT = (
    "I am connecting you to a human agent now. "
    "Please stay on the line."
)

def extract_reply_text(agent_response: dict) -> str:
    """
    Converts structured agent output into speakable text for TTS
    """
    if not agent_response:
        return "Sorry, I could not process that."

    result = agent_response.get("result", {})

    if isinstance(result, str):
        return result

    if isinstance(result, dict):
        if "reply" in result:
            return result["reply"]
        if "message" in result:
            return result["message"]
        if "error" in result:
            return f"Sorry, {result['error']}."

    return "I have processed your request."


tts = TTSAdapter()

@app.websocket("/ws/agent")
async def agent_ws(ws: WebSocket):
    await ws.accept()

    while True:
        try:
            # 1️⃣ Receive payload from frontend
            data = await ws.receive_json()
            transcript = data["transcript"]
            session_id = data["session_id"]

            # 2️⃣ Build task payload for executor
            task_payload = {
                "task": "agent",
                "args": {
                    "transcript": transcript
                }
            }

            # 3️⃣ Call executor with CORRECT signature
            agent_response = execute_task(
                db=None,                 # pass DB session if you have one
                task=task_payload,
                session_id=session_id
            )

            # 🔍 DEBUG LOGS
            print("AGENT RESPONSE:", agent_response)

            # 4️⃣ Extract speakable text
            reply_text = extract_reply_text(agent_response)
            print("TTS TEXT:", reply_text)

            # 5️⃣ Generate TTS
            wav_path = tts.synthesize(reply_text)
            print("TTS WAV PATH:", wav_path)

            # 6️⃣ Stream bot reply audio
            await stream_wav_over_ws(ws, wav_path)

            # 7️⃣ Escalation flow (ONLY if triggered)
            if agent_response.get("result", {}).get("needs_human"):
                escalation_wav = tts.synthesize(ESCALATION_VOICE_PROMPT)
                print("ESCALATION WAV:", escalation_wav)

                await stream_wav_over_ws(ws, escalation_wav)

                await ws.send_json({
                    "type": "escalation",
                    "message": "Human agent requested"
                })

        except Exception as e:
            print("WS AGENT ERROR:", e)
            await ws.send_json({
                "type": "error",
                "message": str(e)
            })
            break


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
        
    def extract_reply_text(agent_response: dict) -> str:
    #Converts structured agent output into a speakable string for TTS
        if not agent_response:
            return "Sorry, I could not process that."
            result = agent_response.get("result", {})
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            if "reply" in result:
                return result["reply"]
        if "message" in result:
            return result["message"]
        if "error" in result:
            return f"Sorry, {result['error']}."
    return "I have processed your request."


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
