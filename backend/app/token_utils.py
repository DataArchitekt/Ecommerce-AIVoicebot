# backend/app/token_utils.py
import os
import time
import uuid
from typing import Optional
import jwt
from fastapi import HTTPException

def make_livekit_token(room: str = "test-room", identity: Optional[str] = None) -> str:
    """
    Generates a LiveKit JWT for joining a room.
    Compatible with Python 3.9 (uses Optional from typing).
    """
    api_key = os.environ.get("LIVEKIT_API_KEY")
    api_secret = os.environ.get("LIVEKIT_API_SECRET")

    if not api_key or not api_secret:
        raise HTTPException(
            status_code=500,
            detail="LIVEKIT_API_KEY or LIVEKIT_API_SECRET missing in environment"
        )

    if not identity:
        identity = f"user-{uuid.uuid4().hex[:8]}"

    now = int(time.time())
    payload = {
        "jti": str(uuid.uuid4()),
        "iss": api_key,
        "nbf": now,
        "exp": now + 60 * 60,
        "grants": {
            "video": {
                "room": room,
                "roomJoin": True,
            },
            "identity": identity
        }
    }

    token = jwt.encode(payload, api_secret, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token
