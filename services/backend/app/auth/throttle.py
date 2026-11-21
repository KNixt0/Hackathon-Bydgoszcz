"""Login throttling: failed attempts per e-mail and per client IP in a sliding window.

In-memory, so it is per API process (the compose stack runs one). A success clears the e-mail's counter.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from app.config import get_settings


class LoginThrottle:
    def __init__(self) -> None:
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float, window: float) -> deque[float]:
        bucket = self._failures[key]
        while bucket and bucket[0] <= now - window:
            bucket.popleft()
        if not bucket:
            self._failures.pop(key, None)
        return bucket

    def retry_after(self, email: str, ip: str) -> int:
        """Seconds to wait, or 0 when another attempt is allowed."""
        settings = get_settings()
        window = float(settings.login_window_seconds)
        now = time.monotonic()
        wait = 0.0
        with self._lock:
            for key, limit in (
                (f"e:{email}", settings.login_max_failures_per_email),
                (f"i:{ip}", settings.login_max_failures_per_ip),
            ):
                bucket = self._prune(key, now, window)
                if len(bucket) >= limit:
                    wait = max(wait, bucket[0] + window - now)
        return int(wait) + 1 if wait > 0 else 0

    def failure(self, email: str, ip: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._failures[f"e:{email}"].append(now)
            self._failures[f"i:{ip}"].append(now)

    def success(self, email: str) -> None:
        with self._lock:
            self._failures.pop(f"e:{email}", None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


throttle = LoginThrottle()
