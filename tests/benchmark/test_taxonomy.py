"""Taxonomy contracts: status vocabulary, check kinds, trial aggregation."""

from geocase.benchmark.taxonomy import (
    TRAP_CATEGORIES,
    CheckKind,
    CheckResult,
    Status,
    aggregate_outcome,
)


def _check(status: Status, kind: CheckKind = CheckKind.EDGE) -> CheckResult:
    return CheckResult(check="c", kind=kind, status=status, detail="")


def test_status_values():
    assert {s.value for s in Status} == {"PASS", "SILENT", "LOUD", "MISSING"}


def test_check_kind_values():
    assert {k.value for k in CheckKind} == {"control", "edge"}


def test_trap_categories_are_the_controlled_vocabulary():
    assert TRAP_CATEGORIES == frozenset(
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
            "encoding",
        }
    )


def test_aggregate_missing_wins():
    assert aggregate_outcome([_check(Status.MISSING)]) == "MISSING"


def test_aggregate_silent_beats_loud():
    checks = [_check(Status.LOUD), _check(Status.SILENT), _check(Status.PASS)]
    assert aggregate_outcome(checks) == "SILENT"


def test_aggregate_loud_beats_correct():
    assert aggregate_outcome([_check(Status.PASS), _check(Status.LOUD)]) == "LOUD"


def test_aggregate_all_pass_is_correct():
    assert aggregate_outcome([_check(Status.PASS), _check(Status.PASS)]) == "CORRECT"
