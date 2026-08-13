"""Status taxonomy and result models (Plan 15 Phase 1).

Semantics ported verbatim from the Step 0 grader: a check that raises is LOUD
(the agent's own test run would have caught it), a wrong value returned without
an exception is SILENT, and SILENT dominates LOUD when aggregating a trial.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

GEO_TRAP_CATEGORIES = frozenset(
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
        # Plan 17 Phase 3: format-level traps with no geodesy in them. DBF's
        # 10-character field-name limit is normative, so the oracle is stated
        # from the spec rather than computed.
        "encoding",
        # Plan 18 Phase 0: facts published in a product specification that no
        # amount of reasoning recovers — Sentinel-2 baseline 04.00's
        # BOA_ADD_OFFSET, the quantification value, the SCL class codes.
        "product-spec",
    }
)

STDLIB_TRAP_CATEGORIES = frozenset(
    {
        "normalization",
        "null-propagation",
        "rounding-residue",
        "dst-transition",
        "cancellation",
        "quoting",
    }
)

# Per-domain rather than one flat set: a geo task must not be able to declare a
# numeric category, and vice versa. Namespacing the strings instead would have
# rewritten all 13 geo values inside the pin at
# ``tests/benchmark/test_taxonomy.py``, destroying its value as a drift check.
TRAP_CATEGORIES_BY_DOMAIN: dict[str, frozenset[str]] = {
    "geo": GEO_TRAP_CATEGORIES,
    "stdlib": STDLIB_TRAP_CATEGORIES,
}

# Back-compat alias: the geo vocabulary is what ``TRAP_CATEGORIES`` always meant.
TRAP_CATEGORIES = GEO_TRAP_CATEGORIES


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
