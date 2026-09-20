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

# Plan 46 §2.3: which catalog ``risk_types`` terms a trap category exercises.
#
# The two vocabularies were disjoint, which is how ``transform/*``, ``dtype/*``
# and ``precision/*`` came to have purpose-built corpus cases and zero
# benchmark coverage without anyone noticing. This dict is *data*: it imports
# nothing from ``geocase.catalog`` (``tests/benchmark/test_fixture_isolation.py``
# keeps ``fixtures.py`` the sole importer), and
# ``tests/benchmark/test_trap_coverage.py`` checks every term against
# ``geocase.catalog.risk_types`` so an unaliased rename fails loudly.
#
# Mapped conservatively — a term is listed only where the task's trap *is*
# that failure mode, not where it is merely nearby — because the coverage
# report (``report --coverage``) reads gaps off this table, and an optimistic
# mapping would hide exactly the gaps it exists to show.
TRAP_TO_RISK: dict[str, tuple[str, ...]] = {
    # ---- geo
    "antimeridian": ("extent/antimeridian", "extent/coordinate_wrapping"),
    "axis-order": ("crs/axis_order", "crs/lat_lon_swap"),
    "units-degrees": (
        "crs/units",
        "crs/projected_coordinate_assumption",
        "measurement/distance_error",
    ),
    "crs-conformance": ("crs/mishandled",),
    "nodata": ("nodata/ignored", "measurement/incorrect_statistics"),
    "topology-repair": ("geometry/repair_variability", "geometry/silent_invalid"),
    "canonical-equality": ("geometry/ring_orientation",),
    "predicate-semantics": ("data/coordinate_edge_case",),
    # voronoi_cells: output order must match input order. No catalog term
    # names an output-index contract; see UNMAPPED_TRAPS.
    "ordering": (),
    # tile_bounds: TMS row inversion is a tile-scheme convention, not a raster
    # geotransform, so it does *not* count as transform/bottom_up coverage.
    "y-flip": ("extent/bbox_misinterpretation",),
    "zone-exceptions": ("crs/zone_selection",),
    "collinearity": (
        "geometry/degenerate_but_parseable",
        "geometry/false_positive_intersection",
    ),
    "discretization": ("crs/reprojection_error", "geometry/simplification_loss"),
    "encoding": ("attribute/field_name_truncation", "format/limitation"),
    "product-spec": ("scaling/ignored", "nodata/ignored"),
    # ---- stdlib. The catalog is geospatial; a term is listed only where the
    # failure mode is literally the same one.
    "normalization": (),
    "null-propagation": ("nodata/default_value_sink", "data/nan_propagation"),
    "rounding-residue": ("precision/loss",),
    "dst-transition": ("attribute/timezone_normalization",),
    "cancellation": ("precision/loss",),
    "quoting": (),
}

#: Categories with no honest catalog counterpart, and why. Every entry here
#: maps to ``()`` above; the test refuses an empty mapping without a reason.
UNMAPPED_TRAPS: dict[str, str] = {
    "ordering": (
        "an output-index contract (cell i belongs to point i); the catalog "
        "names no failure mode for result ordering"
    ),
    "normalization": (
        "Unicode NFC/NFD folding; the catalog has no text-normalization term"
    ),
    "quoting": "CSV quoting; not a geospatial failure mode",
}


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


TrialClass = Literal["correct", "trapped", "broken", "loud", "missing"]


def classify_trial(checks: list[CheckResult]) -> TrialClass:
    """``trapped`` vs ``broken``, derived from the checks (Plan 46 §2.1).

    :func:`aggregate_outcome` scores a failed control and a failed edge the
    same ``SILENT``. Those are different findings: ``broken`` is a model that
    cannot do the job (a control did not pass), ``trapped`` is the phenomenon
    the benchmark is about — every control passes and an edge returns a
    plausible wrong value. ``correct``/``loud``/``missing`` are the existing
    verdicts under report-time names, so the two functions never disagree
    where they overlap.

    Computed at report time and **never written into a record**: every
    existing ``run.json`` already carries the check-level detail this needs,
    and Plan 45's byte-identical regeneration requirement stands.
    """
    statuses = {c.status for c in checks}
    if Status.MISSING in statuses:
        return "missing"
    if any(c.kind is CheckKind.CONTROL and c.status is not Status.PASS for c in checks):
        return "broken"
    if any(c.kind is CheckKind.EDGE and c.status is Status.SILENT for c in checks):
        return "trapped"
    if Status.LOUD in statuses:
        return "loud"
    return "correct"


class TrialOutcome(BaseModel):
    task: str
    outcome: TrialVerdict
    checks: list[CheckResult]
