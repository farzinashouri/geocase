Exact rational arithmetic (floats convert to `Fraction` losslessly) so the "one point / many points / none" decision is never a tolerance guess:

```python
"""Exact planar line-segment intersection.

``segment_intersection(a, b)`` reports what two 2D segments have in common:

* ``None``                         - the segments are disjoint,
* ``(x, y)``                       - they meet in exactly one point,
* ``((xa, ya), (xb, yb))``         - they overlap along a sub-segment.

Each input segment is ``((x1, y1), (x2, y2))`` in a planar (projected)
coordinate system; degenerate segments whose endpoints coincide are accepted
and treated as points.

All intersection predicates -- parallelism, collinearity, and the in-range
tests on the segment parameters -- are evaluated in exact rational arithmetic.
Every finite float is exactly a rational, so converting the inputs to
``fractions.Fraction`` loses nothing and the branch taken is the mathematically
correct one for the coordinates as given; there is no tolerance to tune and no
near-parallel case that silently flips. Only the final coordinates are rounded
back to float, so a returned point can differ from the true intersection by an
ulp or two, but never at the cost of the classification itself.

When the result is an overlap, its endpoints are ordered along ``a``, running
from the end nearer ``a[0]`` to the end nearer ``a[1]``.
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Optional, Tuple, Union

__all__ = ["segment_intersection"]

Point = Tuple[float, float]
Segment = Tuple[Point, Point]
Intersection = Union[None, Point, Segment]

_Vec = Tuple[Fraction, Fraction]

_ZERO = Fraction(0)
_ONE = Fraction(1)


def _exact(value: object) -> Fraction:
    """Convert a single coordinate to an exact rational."""
    number = float(value)  # type: ignore[arg-type]
    if not math.isfinite(number):
        raise ValueError(f"coordinate must be finite, got {value!r}")
    return Fraction(number)


def _point(raw: object) -> _Vec:
    x, y = raw  # type: ignore[misc]
    return _exact(x), _exact(y)


def _segment(raw: object, name: str) -> Tuple[_Vec, _Vec]:
    try:
        start, end = raw  # type: ignore[misc]
        return _point(start), _point(end)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{name} must be a segment ((x1, y1), (x2, y2)); got {raw!r}"
        ) from exc


def _sub(u: _Vec, v: _Vec) -> _Vec:
    return u[0] - v[0], u[1] - v[1]


def _cross(u: _Vec, v: _Vec) -> Fraction:
    return u[0] * v[1] - u[1] * v[0]


def _dot(u: _Vec, v: _Vec) -> Fraction:
    return u[0] * v[0] + u[1] * v[1]


def _along(origin: _Vec, direction: _Vec, t: Fraction) -> Point:
    """The point ``origin + t * direction``, as floats."""
    return float(origin[0] + t * direction[0]), float(origin[1] + t * direction[1])


def _covers(start: _Vec, direction: _Vec, probe: _Vec) -> bool:
    """True if ``probe`` lies on the segment ``start -> start + direction``."""
    offset = _sub(probe, start)
    if _cross(offset, direction) != _ZERO:
        return False
    projection = _dot(offset, direction)
    return _ZERO <= projection <= _dot(direction, direction)


def segment_intersection(a: Segment, b: Segment) -> Intersection:
    """Intersect two planar line segments.

    Args:
        a: First segment as ``((x1, y1), (x2, y2))``.
        b: Second segment, same form.

    Returns:
        ``None`` when the segments share no point, ``(x, y)`` when they share
        exactly one, or ``((xa, ya), (xb, yb))`` when they share a sub-segment.

    Raises:
        ValueError: If either argument is not a pair of coordinate pairs, or
            any coordinate is NaN or infinite.
    """
    p0, p1 = _segment(a, "a")
    q0, q1 = _segment(b, "b")

    r = _sub(p1, p0)
    s = _sub(q1, q0)
    a_is_point = r == (_ZERO, _ZERO)
    b_is_point = s == (_ZERO, _ZERO)

    # Degenerate segments: point/point and point/segment containment.
    if a_is_point and b_is_point:
        return (float(p0[0]), float(p0[1])) if p0 == q0 else None
    if a_is_point:
        return (float(p0[0]), float(p0[1])) if _covers(q0, s, p0) else None
    if b_is_point:
        return (float(q0[0]), float(q0[1])) if _covers(p0, r, q0) else None

    offset = _sub(q0, p0)
    denominator = _cross(r, s)

    if denominator != _ZERO:
        # Non-parallel: a unique intersection of the supporting lines, which
        # counts only if it falls inside both segments.
        t = _cross(offset, s) / denominator
        u = _cross(offset, r) / denominator
        if _ZERO <= t <= _ONE and _ZERO <= u <= _ONE:
            return _along(p0, r, t)
        return None

    # Parallel. Distinct supporting lines never meet.
    if _cross(offset, r) != _ZERO:
        return None

    # Collinear: intersect the two parameter ranges along ``a``.
    scale = _dot(r, r)
    t_start = _dot(offset, r) / scale
    t_end = _dot(_sub(q1, p0), r) / scale
    if t_start > t_end:
        t_start, t_end = t_end, t_start

    low = max(t_start, _ZERO)
    high = min(t_end, _ONE)
    if low > high:
        return None
    if low == high:
        return _along(p0, r, low)
    return _along(p0, r, low), _along(p0, r, high)
```