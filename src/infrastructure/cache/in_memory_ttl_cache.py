from __future__ import annotations

import threading
import time
from typing import Generic, TypeVar

T = TypeVar("T")


class InMemoryTTLCache(Generic[T]):
    """Small process-local TTL cache for repeated expensive computations."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[str, tuple[float, T]] = {}

    def get(self, key: str) -> T | None:
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, value = entry
            if expires_at <= now:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: T, ttl_seconds: int) -> None:
        expires_at = time.time() + max(1, ttl_seconds)
        with self._lock:
            self._store[key] = (expires_at, value)
