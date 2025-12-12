# gen_token.py
import os, jwt, time, uuid

api_key = os.environ["LIVEKIT_API_KEY"]
api_secret = os.environ["LIVEKIT_API_SECRET"]

identity = "alice"
room = "test-room"

now = int(time.time())
payload = {
    "jti": str(uuid.uuid4()),
    "iss": api_key,
    "nbf": now,
    "exp": now + 60*60,   # token valid 1 hour
    "grants": {
        "video": {
            "room": room,
            "roomJoin": True,
            "canPublish": True,
            "canSubscribe": True
        },
        "identity": identity
    }
}

token = jwt.encode(payload, api_secret, algorithm="HS256")
print(token)