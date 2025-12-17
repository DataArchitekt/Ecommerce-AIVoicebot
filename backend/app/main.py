# backend/app/main.py
# backend/app/main.py
from pathlib import Path
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────
# ENV LOADING (must happen before tracer creation)
# ─────────────────────────────────────────────────────────────
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

import os
import uuid
import re
import wave
from fastapi import FastAPI, HTTPException, WebSocketDisconnect
from pydantic import BaseModel
from fastapi import WebSocket, Depends
from backend.app.tts_adapter import TTSAdapter
from backend.app.ws_audio_out import stream_wav_over_ws
from backend.app.stt_file import router as stt_router
from backend.app.metrics import REQUEST_COUNT, REQUEST_LATENCY
from prometheus_client import make_asgi_app
import time
from backend.app.metrics import PII_BLOCK_COUNT
from fastapi.middleware.cors import CORSMiddleware
from backend.app.agents.agent_runner import run_with_evaluation

import backend.app.db as db
from typing import Optional
from backend.app.db import get_db
from backend.app.mcp_middleware import contains_pii

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
from backend.app.agents.executor import execute_task
from backend.app.agents.trace_helpers import (
    make_langchain_tracer,
    runnable_config_for_tracer,
)


from backend.app.database import SessionLocal

from backend.app.agents.langchain_prompts import build_rag_executor
from backend.app.rag import get_retriever
from langchain_core.runnables import RunnableLambda

ESCALATION_VOICE_PROMPT = (
    "I am connecting you to a human agent now. "
    "Please stay on the line."
)

tts = TTSAdapter()
db = SessionLocal()

# ─────────────────────────────────────────
# WS AUDIO STREAMING HELPER (TOP LEVEL)
# ─────────────────────────────────────────
async def stream_wav_over_ws(ws: WebSocket, wav_path: str):
    """
    Streams a WAV file over WebSocket in binary chunks.
    """
    with wave.open(wav_path, "rb") as wf:
        while True:
            chunk = wf.readframes(1024)
            if not chunk:
                break
            await ws.send_bytes(chunk)

@app.websocket("/ws/agent")
async def agent_ws(ws: WebSocket):
    await ws.accept()
    print("🟢 WS connected")
    # Generate run_id here and tie it to LangSmith trace
    while True:
            try:
                print("🟡 Waiting for WS message...")
                data = await ws.receive_json()
                transcript = data["transcript"]
                session_id = data["session_id"]
                transcript = transcript.strip()
                transcript = re.sub(r"[.?!]+$", "", transcript)
                
                ground_truth = data.get("ground_truth")
                run_id = str(uuid.uuid4())
                run_name = f"session_{session_id}_{run_id[:8]}"
                
                # Start LangSmith trace
                #with trace(
                #    name="ws_agent_session",
                #    run_type="chain",
                #    metadata={"session_id": session_id, "run_id": run_id, "run_name": run_name}
                #) as parent_run:
                agent_response = run_with_evaluation(
                    execute_fn=execute_task,
                    db=db,
                    transcript=transcript,
                    session_id=session_id,
                    ground_truth=ground_truth,
                    run_id=run_id
                )
                await ws.send_json(agent_response)

                # 🔍 DEBUG LOGS
                print("AGENT RESPONSE:", agent_response)

                # 4️⃣ Extract speakable text
                reply_text = agent_response.get("reply", "")
                print("🔊 TTS TEXT:", reply_text)

                if not reply_text.strip():
                    reply_text = "Sorry, I don't have an answer right now."

                # 5️⃣ Generate TTS
                wav_path = tts.synthesize(reply_text)
                print("🔊 TTS WAV PATH:", wav_path)

                # 🔔 AUDIO START (CRITICAL)
                await ws.send_json({
                    "type": "audio_start",
                    "format": "wav"
                })

                # 6️⃣ Stream WAV bytes
                with open(wav_path, "rb") as f:
                    while chunk := f.read(4096):
                        await ws.send_bytes(chunk)
                print("Streaming TTS WAV:", wav_path)

                # 🔔 AUDIO END (CRITICAL)
                await ws.send_json({
                    "type": "audio_end"
                })

                print("TTS WAV size:", os.path.getsize(wav_path))

                # 7️⃣ Escalation flow (ONLY if triggered)
                if agent_response.get("result", {}).get("needs_human"):
                    escalation_wav = tts.synthesize(ESCALATION_VOICE_PROMPT)
                    print("ESCALATION WAV:", escalation_wav)

                    await stream_wav_over_ws(ws, escalation_wav)

                    await ws.send_json({
                        "type": "escalation",
                        "message": "Human agent requested"
                    })
                if contains_pii(transcript):
                    PII_BLOCK_COUNT.inc()
                    return {
                        "reply": "I can't help with that. Connecting you to support.",
                        "actions": ["human_escalation"],
                        "tts_allowed": False
                }
            except WebSocketDisconnect:
                print("🔴 WS client disconnected")
                break
        
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

@app.on_event("startup")
def startup():
    global retriever, rag_executor

    retriever = get_retriever()
    rag_executor = build_rag_executor(retriever)

    print("✅ RAG executor initialized")


# ─────────────────────────────────────────────────────────────
# Request model
# ─────────────────────────────────────────────────────────────
class AgentRequest(BaseModel):
    transcript: str
    session_id: str
    ground_truth: Optional[str] = None

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
def agent_handle(req: AgentRequest, db=Depends(get_db)):
    if not req.transcript:
        raise HTTPException(status_code=400, detail="transcript required")

    start = time.time()
    REQUEST_COUNT.labels(endpoint="/agent/handle").inc()

    run_id = str(uuid.uuid4())
    run_name = f"session_{req.session_id}_{run_id[:8]}"

    try:
        tracer = make_langchain_tracer(
            project_name=os.getenv("LANGSMITH_PROJECT")
        )
        print(f"🧭 LangSmith run_name = {run_name}")
    except Exception:
        tracer = None

    agent_response = run_with_evaluation(
        execute_fn=execute_task,
        db=db,
        transcript=req.transcript,
        session_id=req.session_id,
        ground_truth=getattr(req, "ground_truth", None),
        run_id=run_id
    )

    REQUEST_LATENCY.labels(endpoint="/agent/handle").observe(
        time.time() - start
    )

    db.close()
    return agent_response

# ---- Prometheus Metrics Endpoint ----
from prometheus_client import make_asgi_app

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

