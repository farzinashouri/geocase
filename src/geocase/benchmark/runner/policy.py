"""Shared pacing flags for the orchestrator and the probe script (Plan 17 §1.4).

Both entry points make the same OpenRouter calls against the same account-wide
limits, so they must not drift: one place defines the flags, one place resolves
them against the config, and both call it. The precedence is the usual one —
explicit flag beats config block beats the built-in default.

Config shape (read from ``configs/*.yaml``)::

    limits:
      rpm: 18                          # under the 20 RPM :free cap
      requests_per_day: 950            # 1000/day at >=$10 lifetime credit
      quota_file: .geocase_quota.json  # gitignored, local operator state
    retry:
      max_retry_after: 60
      honor_long_retry_after: true
      max_total_seconds: 180
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from geocase.benchmark.runner.limiter import DailyQuota, RateLimiter
from geocase.benchmark.runner.openrouter import OpenRouterClient, RetryPolicy


@dataclass(frozen=True)
class Pacing:
    """Everything needed to build a paced client, resolved from flags+config."""

    retry: RetryPolicy
    rpm: float | None
    requests_per_day: int | None
    quota_file: Path | None
    max_usd_total: float | None

    def build_client(self, **kwargs: object) -> OpenRouterClient:
        quota = (
            DailyQuota(self.quota_file, self.requests_per_day)
            if self.quota_file is not None and self.requests_per_day is not None
            else None
        )
        return OpenRouterClient(
            policy=self.retry,
            limiter=RateLimiter(self.rpm),
            quota=quota,
            **kwargs,  # type: ignore[arg-type]
        )

    def describe(self) -> str:
        rpm = "unpaced" if self.rpm is None else f"{self.rpm:g} rpm"
        day = (
            "no daily cap"
            if self.requests_per_day is None
            else f"{self.requests_per_day}/day"
        )
        honor = "honoring" if self.retry.honor_long_retry_after else "refusing"
        return (
            f"pacing: {rpm}, {day}; retry <= {self.retry.max_retry_after:g}s "
            f"({honor} longer asks), task budget "
            f"{self.retry.max_total_seconds:g}s"
        )


def add_pacing_args(ap: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Add the pacing/budget flags. Defaults are ``None`` = "use the config"."""
    g = ap.add_argument_group("pacing")
    g.add_argument(
        "--rpm",
        type=float,
        default=None,
        help="account-wide requests per minute (0 or 'none' to disable pacing)",
    )
    g.add_argument(
        "--requests-per-day",
        type=int,
        default=None,
        help="per-day request cap, persisted across runs; 0 disables",
    )
    g.add_argument(
        "--max-retry-after",
        type=float,
        default=None,
        help="longest server-requested Retry-After this run will consider",
    )
    g.add_argument(
        "--honor-retry-after",
        action="store_true",
        help="sit through a Retry-After longer than --max-retry-after "
        "(off by default: a long silent sleep looks like a hang)",
    )
    g.add_argument(
        "--task-budget",
        type=float,
        default=None,
        help="seconds any single task may consume, retries included",
    )
    g.add_argument(
        "--max-usd",
        type=float,
        default=None,
        help="override budget.max_usd_total from the config",
    )
    return ap


T = TypeVar("T")


def _pick(flag: T | None, cfg: T | None, default: T) -> T:
    """Explicit flag beats config block beats built-in default."""
    if flag is not None:
        return flag
    return default if cfg is None else cfg


def policy_from_args(args: argparse.Namespace, config: dict) -> Pacing:
    """Resolve flags against a config block into a single :class:`Pacing`."""
    limits = config.get("limits") or {}
    retry_cfg = config.get("retry") or {}
    budget = config.get("budget") or {}
    d = RetryPolicy()

    honor = bool(
        getattr(args, "honor_retry_after", False)
        or retry_cfg.get("honor_long_retry_after", d.honor_long_retry_after)
    )
    retry = RetryPolicy(
        max_attempts=int(retry_cfg.get("max_attempts", d.max_attempts)),
        max_timeout_attempts=int(
            retry_cfg.get("max_timeout_attempts", d.max_timeout_attempts)
        ),
        max_retry_after=float(
            _pick(
                getattr(args, "max_retry_after", None),
                retry_cfg.get("max_retry_after"),
                d.max_retry_after,
            )
        ),
        backoff_base=float(retry_cfg.get("backoff_base", d.backoff_base)),
        max_backoff=float(retry_cfg.get("max_backoff", d.max_backoff)),
        max_backoff_long=float(retry_cfg.get("max_backoff_long", d.max_backoff_long)),
        max_total_seconds=float(
            _pick(
                getattr(args, "task_budget", None),
                retry_cfg.get("max_total_seconds"),
                d.max_total_seconds,
            )
        ),
        honor_long_retry_after=honor,
    )

    rpm_raw = _pick(getattr(args, "rpm", None), limits.get("rpm"), None)
    rpm = None if rpm_raw in (None, 0, 0.0) else float(rpm_raw)

    rpd_raw = _pick(
        getattr(args, "requests_per_day", None), limits.get("requests_per_day"), None
    )
    rpd = None if rpd_raw in (None, 0) else int(rpd_raw)

    quota_file = limits.get("quota_file")
    max_usd = _pick(getattr(args, "max_usd", None), budget.get("max_usd_total"), None)
    return Pacing(
        retry=retry,
        rpm=rpm,
        requests_per_day=rpd,
        quota_file=Path(quota_file) if quota_file else None,
        max_usd_total=None if max_usd is None else float(max_usd),
    )
