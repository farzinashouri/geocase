"""Taxonomy contracts: status vocabulary, check kinds, trial aggregation."""

from geocase.benchmark.taxonomy import (
    TRAP_CATEGORIES,
    CheckKind,
    CheckResult,
    Status,
    aggregate_outcome,
    classify_trial,
)


def _check(status: Status, kind: CheckKind | None = CheckKind.EDGE) -> CheckResult:
    return CheckResult(check="c", kind=kind, status=status, detail="")


_CTRL, _EDGE = CheckKind.CONTROL, CheckKind.EDGE


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
            "product-spec",
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


# ------------------------------------------- Plan 46 §2.1: trapped vs broken
# Both aggregate to SILENT; they are different findings. `trapped` is the
# phenomenon the benchmark is about — the easy cases pass and the edge returns
# a plausible wrong value. `broken` is a model that cannot do the job at all.
# Derived at report time from the stored checks, never written into a record.


def test_trapped_requires_controls_to_pass():
    checks = [_check(Status.SILENT, _CTRL), _check(Status.PASS, _EDGE)]
    assert aggregate_outcome(checks) == "SILENT"
    assert classify_trial(checks) == "broken"


def test_silent_edge_over_passing_controls_is_trapped():
    checks = [_check(Status.PASS, _CTRL), _check(Status.SILENT, _EDGE)]
    assert classify_trial(checks) == "trapped"


def test_a_crashing_control_is_broken_not_trapped():
    """A LOUD control with a SILENT edge: the model cannot do the easy case."""
    checks = [_check(Status.LOUD, _CTRL), _check(Status.SILENT, _EDGE)]
    assert aggregate_outcome(checks) == "SILENT"
    assert classify_trial(checks) == "broken"


def test_classify_missing_wins():
    checks = [_check(Status.MISSING, None), _check(Status.SILENT, _EDGE)]
    assert classify_trial(checks) == "missing"


def test_classify_loud_edge_over_passing_controls_is_loud():
    checks = [_check(Status.PASS, _CTRL), _check(Status.LOUD, _EDGE)]
    assert classify_trial(checks) == "loud"


def test_classify_import_crash_is_loud():
    assert classify_trial([_check(Status.LOUD, None)]) == "loud"


def test_classify_all_pass_is_correct():
    checks = [_check(Status.PASS, _CTRL), _check(Status.PASS, _EDGE)]
    assert classify_trial(checks) == "correct"


def test_classify_agrees_with_aggregate_where_they_overlap():
    """`correct`/`loud`/`missing` are the old verdicts under new names; only
    SILENT splits. A classification must never contradict the stored verdict."""
    table = {
        "correct": [_check(Status.PASS, _CTRL), _check(Status.PASS, _EDGE)],
        "loud": [_check(Status.PASS, _CTRL), _check(Status.LOUD, _EDGE)],
        "missing": [_check(Status.MISSING, None)],
        "trapped": [_check(Status.PASS, _CTRL), _check(Status.SILENT, _EDGE)],
        "broken": [_check(Status.SILENT, _CTRL), _check(Status.PASS, _EDGE)],
    }
    verdict_of = {
        "correct": "CORRECT",
        "loud": "LOUD",
        "missing": "MISSING",
        "trapped": "SILENT",
        "broken": "SILENT",
    }
    for expected, checks in table.items():
        assert classify_trial(checks) == expected
        assert aggregate_outcome(checks) == verdict_of[expected]
