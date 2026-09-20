"""Exact planar segment/segment intersection.

The public entry point is :func:`segment_intersection`, which reports the
geometric intersection of two 2D line segments as either ``None`` (no common
point), a point (exactly one common point), or a segment (the shared portion
when the two segments overlap collinearly).

All predicates and coordinates are evaluated in exact rational arithmetic:
binary floats convert to :class:`fractions.Fraction` losslessly, so the
topological decisions (parallel vs. crossing, touching vs. overlapping,
endpoint-on-segment) are made without rounding error, and only the final
coordinates are rounded back to ``float``.
"""

from __future__ import annotations

from fractions import Fraction
from math import isfinite
from typing import Sequence, Tuple, Union

__all__ = ["segment_intersection"]

Point = Tuple[float, float]
Segment = Tuple[Point, Point]
Result = Union[None, Point, Segment]

_Rational = Tuple[Fraction, Fraction]

_ZERO = Fraction(0)
_ONE = Fraction(1)


def _as_point(value: Sequence[float], label: str) -> _Rational:
    """Convert ``(x, y)`` to an exact rational pair."""
    try:
        x, y = value
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a pair (x, y)") from None
    try:
        x = float(x)
        y = float(y)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must have numeric coordinates") from None
    if not (isfinite(x) and isfinite(y)):
        raise ValueError(f"{label} must have finite coordinates")
    return Fraction(x), Fraction(y)


def _as_segment(value: Sequence[Sequence[float]], label: str) -> Tuple[_Rational, _Rational]:
    try:
        start, end = value
    except (TypeError, ValueError):
        raise ValueError(
            f"{label} must be a pair of points ((x1, y1), (x2, y2))"
        ) from None
    return _as_point(start, f"{label} start"), _as_point(end, f"{label} end")


def _point(x: Fraction, y: Fraction) -> Point:
    return float(x), float(y)


def _contains(px: Fraction, py: Fraction,
              ox: Fraction, oy: Fraction,
              dx: Fraction, dy: Fraction) -> bool:
    """Is the point ``p`` on the non-degenerate segment ``o -> o + d``?"""
    wx, wy = px - ox, py - oy
    if wx * dy - wy * dx != 0:  # not collinear with the supporting line
        return False
    projection = wx * dx + wy * dy
    return _ZERO <= projection <= dx * dx + dy * dy


def segment_intersection(a: Segment, b: Segment) -> Result:
    """Intersect two 2D line segments.

    Parameters
    ----------
    a, b:
        Segments given as ``((x1, y1), (x2, y2))`` with float coordinates in a
        planar (Cartesian) system. Degenerate segments whose two endpoints
        coincide are accepted and treated as points.

    Returns
    -------
    ``None``
        The segments have no point in common.
    ``(x, y)``
        The segments have exactly one point in common.
    ``((xa, ya), (xb, yb))``
        The segments overlap collinearly in more than one point; the returned
        endpoints delimit the shared portion, ordered along the direction of
        ``a``.

    Raises
    ------
    ValueError
        If an argument is not a pair of pairs of finite numbers.
    """
    (p1x, p1y), (p2x, p2y) = _as_segment(a, "a")
    (q1x, q1y), (q2x, q2y) = _as_segment(b, "b")

    # Direction vectors: a spans p1 -> p1 + r, b spans q1 -> q1 + s.
    rx, ry = p2x - p1x, p2y - p1y
    sx, sy = q2x - q1x, q2y - q1y

    a_is_point = rx == 0 and ry == 0
    b_is_point = sx == 0 and sy == 0

    if a_is_point and b_is_point:
        if p1x == q1x and p1y == q1y:
            return _point(p1x, p1y)
        return None
    if a_is_point:
        if _contains(p1x, p1y, q1x, q1y, sx, sy):
            return _point(p1x, p1y)
        return None
    if b_is_point:
        if _contains(q1x, q1y, p1x, p1y, rx, ry):
            return _point(q1x, q1y)
        return None

    wx, wy = q1x - p1x, q1y - p1y
    denominator = rx * sy - ry * sx

    if denominator != 0:
        # Non-parallel: solve p1 + t*r == q1 + u*s for t and u.
        t = (wx * sy - wy * sx) / denominator
        u = (wx * ry - wy * rx) / denominator
        if _ZERO <= t <= _ONE and _ZERO <= u <= _ONE:
            return _point(p1x + t * rx, p1y + t * ry)
        return None

    if wx * ry - wy * rx != 0:
        # Parallel, but on different supporting lines.
        return None

    # Collinear: intersect the parameter intervals along a's direction. The
    # endpoints of b map to t0 and t1; a itself occupies [0, 1].
    rr = rx * rx + ry * ry
    t0 = (wx * rx + wy * ry) / rr
    t1 = ((q2x - p1x) * rx + (q2y - p1y) * ry) / rr
    low, high = (t0, t1) if t0 <= t1 else (t1, t0)
    low = max(low, _ZERO)
    high = min(high, _ONE)

    if low > high:
        return None
    if low == high:
        return _point(p1x + low * rx, p1y + low * ry)
    return (
        _point(p1x + low * rx, p1y + low * ry),
        _point(p1x + high * rx, p1y + high * ry),
    )