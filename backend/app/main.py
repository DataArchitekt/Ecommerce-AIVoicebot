# backend/app/main.py
"""
Minimal Day-1 backend:
- /livekit/token (uses token_utils if present; harmless stub otherwise)
- /stt/file  (file upload -> transcribe_file)
- /stt/ws    (websocket: receive binary chunks, send "EOS" to finalize -> transcript)
- /_env      (debug env presence)
- /health    (healthcheck)
"""

from pathlib import Path
from dotenv import load_dotenv
import os
import tempfile
import shutil
import time
import logging

from typing import Optional

from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# try to load dotenv from project root (../..)
ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
if ROOT_ENV.exists():
    load_dotenv(ROOT_ENV)
else:
    print("WARNING: .env not found at", ROOT_ENV)

# try import token utils (may not exist); try import stt_adapter (should exist)
try:
    from app.token_utils import make_livekit_token
except Exception as e:
    make_livekit_token = None
    print("token_utils import failed (ok for local dev):", e)

try:
    from app.stt_adapter import transcribe_file
except Exception as e:
    print("stt_adapter import failed; using fallback stub:", e)
    def transcribe_file(path: str) -> str:
        return "TRANSCRIPT_PLACEHOLDER"

app = FastAPI(title="Ecommerce Voicebot - Day1 Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/_env")
def _env():
    return {
        "LIVEKIT_API_KEY": bool(os.environ.get("LIVEKIT_API_KEY")),
        "LIVEKIT_API_SECRET": bool(os.environ.get("LIVEKIT_API_SECRET")),
        "STT_MODEL": os.environ.get("STT_MODEL"),
    }

@app.get("/health")
def health():
    return {"status": "ok", "time": int(time.time())}

# Token endpoint (uses token_utils if present - harmless local stub if not)
@app.get("/livekit/token")
def get_livekit_token(room: str = Query("test-room"), identity: Optional[str] = Query(None)):
    if make_livekit_token is None:
        # return a harmless stub token for local dev
        return PlainTextResponse("LOCAL-STUB-TOKEN")
    token = make_livekit_token(room=room, identity=identity)
    return PlainTextResponse(str(token).strip())

# STT file upload endpoint
@app.post("/stt/file")
async def stt_file(file: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp(prefix="stt_")
    try:
        path = os.path.join(temp_dir, file.filename)
        with open(path, "wb") as f:
            f.write(await file.read())
        transcript = transcribe_file(path)
        return {"transcript": transcript}
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

# WebSocket streaming STT
@app.websocket("/stt/ws")
async def stt_ws(websocket: WebSocket):
    """
    Receives binary audio chunks (from MediaRecorder as arrayBuffer). When client sends text "EOS",
    server runs transcribe_file on the accumulated file and replies with {"transcript": "..."}.
    """
    await websocket.accept()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
    tmp_path = tmp.name
    tmp.close()
    logging.info("STT WS: writing to %s", tmp_path)
    try:
        while True:
            msg = await websocket.receive()
            # binary frames -> key "bytes"
            if "bytes" in msg:
                with open(tmp_path, "ab") as f:
                    f.write(msg["bytes"])
            elif "text" in msg:
                text = msg["text"]
                if text == "EOS":
                    try:
                        transcript = transcribe_file(tmp_path)
                        await websocket.send_json({"transcript": transcript})
                    except Exception as e:
                        await websocket.send_json({"error": str(e)})
                    finally:
                        await websocket.close()
                        break
                else:
                    await websocket.send_text("ACK:" + text)
            elif msg.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect()
    except WebSocketDisconnect:
        logging.info("WS client disconnected; attempting finalize if data available")
        try:
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                t = transcribe_file(tmp_path)
                logging.info("Partial transcript on disconnect: %s", t)
        except Exception as e:
            logging.exception("Error finalizing transcript on disconnect: %s", e)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
