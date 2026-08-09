"""Status taxonomy and result models (Plan 15 Phase 1).

Semantics ported verbatim from the Step 0 grader: a check that raises is LOUD
(the agent's own test run would have caught it), a wrong value returned without
an exception is SILENT, and SILENT dominates LOUD when aggregating a trial.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

TRAP_CATEGORIES = frozenset(
    {
        "antimeridian",
        "axis-order",
        "units-degrees",
        "crs-conformance",
        "nodata",
        "topology-repair",
        "canonical-equality",
        "predicate-semantics",
        "ordering",
        "y-flip",
        "zone-exceptions",
        "collinearity",
        "discretization",
    }
)


class Status(StrEnum):
    PASS = "PASS"
    SILENT = "SILENT"
    LOUD = "LOUD"
    MISSING = "MISSING"


class CheckKind(StrEnum):
    CONTROL = "control"
    EDGE = "edge"


class CheckResult(BaseModel):
    check: str
    # None for module-level records (import failure, absent function), which
    # the CLI renders as "-" exactly as the Step 0 grader did.
    kind: CheckKind | None
    status: Status
    detail: str = ""


TrialVerdict = Literal["CORRECT", "SILENT", "LOUD", "MISSING"]


def aggregate_outcome(checks: list[CheckResult]) -> TrialVerdict:
    statuses = {c.status for c in checks}
    if Status.MISSING in statuses:
        return "MISSING"
    if Status.SILENT in statuses:
        return "SILENT"
    if Status.LOUD in statuses:
        return "LOUD"
    return "CORRECT"


class TrialOutcome(BaseModel):
    task: str
    outcome: TrialVerdict
    checks: list[CheckResult]
