"""Account-wide request pacing (Plan 17 Phase 1.2).

OpenRouter's ``:free`` limits are per *account*, not per model or per process:
20 requests/minute account-wide, and 50 requests/day under $10 lifetime credit
(1000/day at or above it). A ``--delay`` between sequential calls paces nothing
once several models interleave, and it cannot see a retry at all — which is why
the 2026-08-11 sweep landed 25 of 160 completions.

Two pieces, deliberately separate because they fail differently:

* :class:`RateLimiter` *blocks*. A per-minute cap clears on its own within
  seconds, so waiting is the correct response.
* :class:`DailyQuota` *raises*. A per-day cap does not clear inside any run, so
  blocking on it would be indistinguishable from a hang; it is persisted to disk
  so a same-day re-run does not re-spend a quota already burnt.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from datetime import date
from pathlib import Path


class QuotaExhaustedError(RuntimeError):
    """The per-day request cap is spent. Not retryable inside this run."""


class RateLimiter:
    """Thread-safe token bucket. ``rpm=None`` disables it (paid models).

    The bucket refills continuously rather than per-window, so a run does not
    fire ``burst`` requests at the top of each minute and then stall — that
    pattern is what trips the provider's own window accounting.
    """

    def __init__(self, rpm: float | None, *, burst: int | None = None):
        if rpm is not None and rpm <= 0:
            raise ValueError(f"rpm must be positive or None, got {rpm!r}")
        self.rpm = rpm
        # One request of slack by default: enough to not serialise the very
        # first call behind a full refill interval, not enough to burst into
        # the provider's window.
        self.capacity = float(burst if burst is not None else 1)
        self._tokens = self.capacity
        self._updated = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> float:
        """Block until a request may be sent. Returns seconds actually waited."""
        if self.rpm is None:
            return 0.0
        rate = self.rpm / 60.0
        waited = 0.0
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(
                    self.capacity, self._tokens + (now - self._updated) * rate
                )
                self._updated = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return waited
                sleep_for = (1.0 - self._tokens) / rate
            # Sleeping outside the lock: another thread's refill is not
            # blocked by this one's wait.
            time.sleep(sleep_for)
            waited += sleep_for


class DailyQuota:
    """Per-day request cap persisted to disk. ``limit=None`` disables it.

    The counter is keyed by date, so it resets at local midnight without any
    cleanup, and a same-day re-run picks up the count it left behind rather
    than starting from zero against a quota that is already spent.
    """

    def __init__(self, path: Path, limit: int | None):
        self.path = Path(path)
        self.limit = limit
        self._lock = threading.Lock()

    def _read(self) -> tuple[str, int]:
        today = date.today().isoformat()
        try:
            data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return today, 0
        if data.get("date") != today:
            return today, 0
        try:
            return today, int(data.get("count", 0))
        except (TypeError, ValueError):
            return today, 0

    def _write(self, day: str, count: int) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic replace: a crash mid-write must not leave a truncated file
        # that silently reads back as "quota untouched".
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as fh:
                json.dump({"date": day, "count": count}, fh)
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    @property
    def used(self) -> int:
        return self._read()[1]

    @property
    def remaining(self) -> int | None:
        if self.limit is None:
            return None
        return max(0, self.limit - self.used)

    def take(self, n: int = 1) -> None:
        """Consume ``n`` requests of quota, or raise :class:`QuotaExhaustedError`."""
        if self.limit is None:
            return
        with self._lock:
            day, count = self._read()
            if count + n > self.limit:
                raise QuotaExhaustedError(
                    f"daily request quota exhausted: {count}/{self.limit} used "
                    f"on {day} (state: {self.path}). It resets at local midnight; "
                    f"raise limits.requests_per_day only if the account's real "
                    f"cap is higher."
                )
            self._write(day, count + n)
