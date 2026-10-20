"""
Response cache for expensive astrocartography calculations.

ACG generation at 1° resolution takes hundreds of milliseconds; the same birth
payload is typically requested repeatedly (goal refocuses, tab switches,
re-ranking). A small in-process TTL memo keyed by a SHA-256 of the canonical
request payload removes that cost with zero infrastructure.

Thread-safety: FastAPI may run sync endpoints in a threadpool, so access is
guarded with a lock. Entries are (expires_at, value) tuples; expired entries
are lazily dropped on lookup and swept opportunistically on write.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any, Callable

_TTL_SECONDS = 600.0
_MAX_ENTRIES = 256

_store: dict[str, tuple[float, Any]] = {}
_lock = threading.Lock()


def payload_key(*parts: Any) -> str:
    """Stable SHA-256 key from arbitrary JSON-serialisable parts."""
    canonical = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def cached(key: str, producer: Callable[[], Any]) -> Any:
    """Return the cached value for *key*, or compute + store it."""
    now = time.monotonic()
    with _lock:
        entry = _store.get(key)
        if entry is not None and entry[0] > now:
            return entry[1]

    # Produce outside the lock — expensive work must not block other requests.
    value = producer()

    now = time.monotonic()
    with _lock:
        # Opportunistic sweep so the store cannot grow unbounded.
        if len(_store) >= _MAX_ENTRIES:
            expired = [k for k, (exp, _) in _store.items() if exp <= now]
            for k in expired:
                _store.pop(k, None)
            # Still full: drop the oldest entries (insertion order).
            while len(_store) >= _MAX_ENTRIES:
                _store.pop(next(iter(_store)))
        _store[key] = (now + _TTL_SECONDS, value)
    return value
