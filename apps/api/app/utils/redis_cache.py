import threading
import time
from typing import Any, Optional

import redis

from ..settings import settings


class _InMemoryRedis:
    """Minimal Redis-like store for dev/test environments."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[Any, Optional[float]]] = {}
        self._lock = threading.Lock()

    def _purge_expired(self, name: Optional[str] = None) -> None:
        now = time.monotonic()
        with self._lock:
            if name is not None:
                item = self._data.get(name)
                if item is None:
                    return
                _, expires_at = item
                if expires_at is not None and expires_at <= now:
                    self._data.pop(name, None)
                return

            expired = [key for key, (_, exp) in self._data.items() if exp is not None and exp <= now]
            for key in expired:
                self._data.pop(key, None)

    def setex(self, name: str, time_seconds: int, value: Any) -> None:
        expires_at = time.monotonic() + int(time_seconds)
        with self._lock:
            self._data[name] = (value, expires_at)

    def get(self, name: str) -> Optional[str]:
        self._purge_expired(name)
        with self._lock:
            item = self._data.get(name)
            if item is None:
                return None
            value, _ = item
            return value

    def delete(self, name: str) -> None:
        with self._lock:
            self._data.pop(name, None)

    # Compatibility helpers -------------------------------------------------
    def ping(self) -> bool:  # pragma: no cover - identical to redis interface
        return True


_client: redis.Redis | _InMemoryRedis | None = None


def get_redis_client() -> redis.Redis | _InMemoryRedis:
    global _client
    if _client is not None:
        return _client

    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
    except redis.exceptions.RedisError:
        client = _InMemoryRedis()

    _client = client
    return client
