
from collections import deque
import os

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class SessionMemory:
    def __init__(self, max_turns=5):
        self.max_turns = max_turns
        self.local_store = {}

        if REDIS_AVAILABLE and os.getenv("REDIS_URL"):
            self.redis = redis.Redis.from_url(os.getenv("REDIS_URL"))
        else:
            self.redis = None

    def _key(self, session_id):
        return f"session:{session_id}"

    def get(self, session_id):
        if self.redis:
            data = self.redis.lrange(self._key(session_id), 0, -1)
            return [d.decode() for d in data]
        return self.local_store.get(session_id, [])

    def add(self, session_id, text):
        if self.redis:
            self.redis.lpush(self._key(session_id), text)
            self.redis.ltrim(self._key(session_id), 0, self.max_turns - 1)
        else:
            buf = self.local_store.setdefault(
                session_id, deque(maxlen=self.max_turns)
            )
            buf.appendleft(text)
