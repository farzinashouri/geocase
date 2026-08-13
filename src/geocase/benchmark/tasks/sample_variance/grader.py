"""Oracle for sample_variance: catastrophic cancellation.

The textbook one-pass form ``(sum(x^2) - n*mean^2) / (n-1)`` returns exactly
``0.0`` for values sharing a large offset — data with obvious spread reported
as having none, with no exception raised. The natural self-check on small
integers is invariant under the defect, which is what makes this the closest
numeric analogue to ``buffer_m``.
"""

TOL = 1e-9


def _is_float(v):
    return isinstance(v, float) or (isinstance(v, int) and not isinstance(v, bool))


def build_checks(f):
    def small_integers():
        got = f([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
        ok = _is_float(got) and abs(got - 4.571428571428571) <= 1e-9
        return ok, f"got {got!r}, expected 4.571428571428571"

    def single_value_is_none():
        got = f([3.0])
        return got is None, f"got {got!r}, expected None"

    def large_offset():
        # Same spread as [1,2,3,4] — variance is exactly 5/3 — but shifted so
        # that squaring the values loses the deviations to rounding.
        got = f([1e9 + 1.0, 1e9 + 2.0, 1e9 + 3.0, 1e9 + 4.0])
        exp = 5.0 / 3.0
        ok = _is_float(got) and abs(got - exp) <= 1e-6
        return ok, f"got {got!r}, expected {exp!r}"

    return [
        ("small_integers", "control", small_integers),
        ("single_value_is_none", "control", single_value_is_none),
        ("large_offset", "edge", large_offset),
    ]
