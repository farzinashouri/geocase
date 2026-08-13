"""Oracle for group_means: null propagation through an all-null group.

The ``v or 0.0`` idiom (and its cousin, defaulting the accumulator) turns a
group with nothing to average into ``0.0`` — a number where the contract says
``None``. Downstream that is indistinguishable from a genuine zero mean.
"""

TOL = 1e-9


def _close(got, exp):
    return isinstance(got, float) and abs(got - exp) <= TOL


def build_checks(f):
    def plain_groups():
        got = f([("a", 1.0), ("a", 3.0), ("b", 10.0)])
        ok = (
            isinstance(got, dict)
            and set(got) == {"a", "b"}
            and _close(got.get("a"), 2.0)
            and _close(got.get("b"), 10.0)
        )
        return ok, f"got {got!r}, expected {{'a': 2.0, 'b': 10.0}}"

    def nulls_excluded_from_denominator():
        # Mean of the two present values is 3.0; counting the None as a row
        # would give 2.0.
        got = f([("a", 2.0), ("a", None), ("a", 4.0)])
        ok = isinstance(got, dict) and set(got) == {"a"} and _close(got.get("a"), 3.0)
        return ok, f"got {got!r}, expected {{'a': 3.0}}"

    def all_null_group():
        got = f([("a", 1.0), ("b", None), ("b", None)])
        ok = (
            isinstance(got, dict)
            and set(got) == {"a", "b"}
            and _close(got.get("a"), 1.0)
            and got.get("b", "absent") is None
        )
        return ok, f"got {got!r}, expected {{'a': 1.0, 'b': None}}"

    return [
        ("plain_groups", "control", plain_groups),
        ("nulls_excluded_from_denominator", "control", nulls_excluded_from_denominator),
        ("all_null_group", "edge", all_null_group),
    ]
