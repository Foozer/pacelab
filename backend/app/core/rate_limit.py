"""In-process rate limiter.

This is an architecture placeholder for a later shared-store limiter (when the
API is run with more than one worker). It is enough to slow credential stuffing
in a single-process MVP.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            events = [stamp for stamp in self._hits[key] if stamp >= cutoff]
            if len(events) >= limit:
                self._hits[key] = events
                return False
            events.append(now)
            self._hits[key] = events
            return True
