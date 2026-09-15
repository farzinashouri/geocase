```python
"""Exact intersection of two 2D line segments.

``segment_intersection(a, b)`` returns the point set the two segments share, as
one of:

* ``None`` -- the segments are disjoint;
* ``(x, y)`` -- they meet in exactly one point (a crossing, a touch, or two
  collinear segments abutting end to end);
* ``((xa, ya), (xb, yb))`` -- they overlap along a sub-segment, reported in the
  direction of ``a`` (from ``a[0]`` towards ``a[1]``).

Degenerate segments (the two endpoints equal) are accepted and treated as the
single point they describe.

Every finite float *is* a rational number, so the predicates here are evaluated
with :class:`fractions.Fraction` instead of in floating point.  The
classification above is therefore exact for the coordinates actually passed in,
no tolerance is involved, and nearly-parallel input needs no special care.
Coordinates are rounded at most once, on the way out, so an intersection that
falls on an input endpoint reproduces that endpoint bit for bit.  The cost is
speed: rational arithmetic runs roughly an order of magnitude slower than
float, which is irrelevant for one-off queries and would matter for a sweep
over millions of pairs.

Examples
--------
>>> segment_intersection(((0.0, 0.0), (2.0, 2.0)), ((0.0, 2.0), (2.0, 0.0)))
(1.0, 1.0)
>>> segment_intersection(((0.0, 0.0), (2.0, 0.0)), ((1.0, 0.0), (3.0, 0.0)))
((1.0, 0.0), (2.0, 0.0))
>>> segment_intersection(((0.0, 0.0), (1.0, 0.0)), ((0.0, 1.0), (1.0, 1.0))) is None
True
"""

from fractions import Fraction
from math import isfinite

__all__ = ["segment_intersection"]

Point = tuple[float, float]
Segment = tuple[Point, Point]
Intersection = Point | Segment | None

_Vec = tuple[Fraction, Fraction]  # an exact point or displacement


def segment_intersection(a: Segment, b: Segment) -> Intersection:
    """Return the points common to segments ``a`` and ``b``.

    Each segment is ``((x1, y1), (x2, y2))`` in a planar (projected) coordinate
    system.  See the module docstring for the shape of the result.

    Raises:
        TypeError: a segment is not a pair of coordinate pairs.
        ValueError: a coordinate is not finite.
    """
    p1, p2 = _as_segment(a, "a")
    q1, q2 = _as_segment(b, "b")
    ep1, ep2, eq1, eq2 = (_exact(p) for p in (p1, p2, q1, q2))

    # Degenerate segments reduce to point containment tests.
    if ep1 == ep2:
        if eq1 == eq2:
            return p1 if ep1 == eq1 else None
        return p1 if _on_segment(ep1, eq1, eq2) else None
    if eq1 == eq2:
        return q1 if _on_segment(eq1, ep1, ep2) else None

    # a(t) = p1 + t * r for t in [0, 1];  b(u) = q1 + u * s for u in [0, 1].
    r = _sub(ep2, ep1)
    s = _sub(eq2, eq1)
    w = _sub(eq1, ep1)
    denom = _cross(r, s)

    if denom != 0:
        t = _cross(w, s) / denom
        u = _cross(w, r) / denom
        if 0 <= t <= 1 and 0 <= u <= 1:
            return (float(ep1[0] + t * r[0]), float(ep1[1] + t * r[1]))
        return None

    if _cross(w, r) != 0:
        return None  # parallel, on distinct lines

    # Collinear: clip b's parameter interval (in a's parameterisation) to [0, 1].
    # Each surviving endpoint is an untouched input endpoint, so no rounding.
    rr = _dot(r, r)
    tq1 = _dot(w, r) / rr
    tq2 = _dot(_sub(eq2, ep1), r) / rr
    (lo, lo_pt), (hi, hi_pt) = sorted(((tq1, q1), (tq2, q2)), key=lambda c: c[0])
    if lo < 0:
        lo, lo_pt = Fraction(0), p1
    if hi > 1:
        hi, hi_pt = Fraction(1), p2

    if lo > hi:
        return None  # collinear but the extents miss each other
    if lo == hi:
        return lo_pt  # they touch end to end
    return (lo_pt, hi_pt)


def _as_segment(value: object, name: str) -> tuple[Point, Point]:
    """Validate one segment argument, returning its two endpoints as floats."""
    try:
        start, end = value  # type: ignore[misc]
    except (TypeError, ValueError):
        raise TypeError(
            f"{name} must be a pair of endpoints ((x1, y1), (x2, y2)), got {value!r}"
        ) from None
    return _as_point(start, f"{name}[0]"), _as_point(end, f"{name}[1]")


def _as_point(value: object, name: str) -> Point:
    try:
        x, y = value  # type: ignore[misc]
    except (TypeError, ValueError):
        raise TypeError(f"{name} must be a coordinate pair (x, y), got {value!r}") from None
    x, y = float(x), float(y)
    if not (isfinite(x) and isfinite(y)):
        raise ValueError(f"{name} must have finite coordinates, got {value!r}")
    return (x, y)


def _exact(point: Point) -> _Vec:
    """Lift a float point into exact rationals (float -> Fraction is lossless)."""
    return (Fraction(point[0]), Fraction(point[1]))


def _sub(u: _Vec, v: _Vec) -> _Vec:
    return (u[0] - v[0], u[1] - v[1])


def _cross(u: _Vec, v: _Vec) -> Fraction:
    return u[0] * v[1] - u[1] * v[0]


def _dot(u: _Vec, v: _Vec) -> Fraction:
    return u[0] * v[0] + u[1] * v[1]


def _on_segment(point: _Vec, start: _Vec, end: _Vec) -> bool:
    """Exact test: does ``point`` lie on the segment ``start``--``end``?"""
    if _cross(_sub(end, start), _sub(point, start)) != 0:
        return False
    return (
        min(start[0], end[0]) <= point[0] <= max(start[0], end[0])
        and min(start[1], end[1]) <= point[1] <= max(start[1], end[1])
    )
```