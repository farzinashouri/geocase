"""Exact intersection of two 2D line segments.

All geometric decisions (touching, crossing, collinear overlap) are made with
rational arithmetic via ``fractions.Fraction``, so the result is exact for the
given floating-point inputs and shared endpoints are never perturbed by
rounding. Only the final coordinates are converted back to ``float``.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Tuple, Union

__all__ = ["segment_intersection"]

Point = Tuple[float, float]
Segment = Tuple[Point, Point]

_FPoint = Tuple[Fraction, Fraction]


def _to_fraction_point(p) -> _FPoint:
    x, y = p
    try:
        return Fraction(x), Fraction(y)
    except (OverflowError, ValueError) as exc:  # inf / nan
        raise ValueError(f"coordinates must be finite numbers, got {p!r}") from exc


def _to_float_point(p: _FPoint) -> Point:
    return float(p[0]), float(p[1])


def _cross(ax: Fraction, ay: Fraction, bx: Fraction, by: Fraction) -> Fraction:
    return ax * by - ay * bx


def _point_on_segment(p: _FPoint, s0: _FPoint, s1: _FPoint) -> bool:
    """True if ``p`` lies on the (non-degenerate) segment ``s0``-``s1``."""
    if _cross(p[0] - s0[0], p[1] - s0[1], s1[0] - s0[0], s1[1] - s0[1]) != 0:
        return False
    return (
        min(s0[0], s1[0]) <= p[0] <= max(s0[0], s1[0])
        and min(s0[1], s1[1]) <= p[1] <= max(s0[1], s1[1])
    )


def segment_intersection(a: Segment, b: Segment) -> Union[None, Point, Segment]:
    """Intersect two 2D line segments.

    Each segment is ``((x1, y1), (x2, y2))``. Returns

    * ``None`` if the segments share no point,
    * a point ``(x, y)`` if they share exactly one point (a proper crossing,
      an endpoint touching, or collinear segments meeting end to end), or
    * a segment ``((xa, ya), (xb, yb))`` describing the shared portion if they
      overlap along a common line.

    Degenerate (zero-length) segments are treated as points. Non-finite
    coordinates raise ``ValueError``.
    """
    p1, p2 = _to_fraction_point(a[0]), _to_fraction_point(a[1])
    p3, p4 = _to_fraction_point(b[0]), _to_fraction_point(b[1])

    a_is_point = p1 == p2
    b_is_point = p3 == p4

    if a_is_point and b_is_point:
        return _to_float_point(p1) if p1 == p3 else None
    if a_is_point:
        return _to_float_point(p1) if _point_on_segment(p1, p3, p4) else None
    if b_is_point:
        return _to_float_point(p3) if _point_on_segment(p3, p1, p2) else None

    d1x, d1y = p2[0] - p1[0], p2[1] - p1[1]
    d2x, d2y = p4[0] - p3[0], p4[1] - p3[1]
    wx, wy = p3[0] - p1[0], p3[1] - p1[1]

    denom = _cross(d1x, d1y, d2x, d2y)

    if denom != 0:
        # Non-parallel lines: p1 + t*d1 == p3 + u*d2 has a unique solution.
        t = _cross(wx, wy, d2x, d2y) / denom
        u = _cross(wx, wy, d1x, d1y) / denom
        if 0 <= t <= 1 and 0 <= u <= 1:
            return _to_float_point((p1[0] + t * d1x, p1[1] + t * d1y))
        return None

    # Parallel lines: they must also be collinear to share anything.
    if _cross(wx, wy, d1x, d1y) != 0:
        return None

    # Collinear: express b's endpoints as parameters along a, clip to [0, 1].
    dd = d1x * d1x + d1y * d1y
    t0 = (wx * d1x + wy * d1y) / dd
    t1 = ((p4[0] - p1[0]) * d1x + (p4[1] - p1[1]) * d1y) / dd
    if t0 > t1:
        t0, t1 = t1, t0

    lo = max(Fraction(0), t0)
    hi = min(Fraction(1), t1)
    if lo > hi:
        return None

    start = (p1[0] + lo * d1x, p1[1] + lo * d1y)
    if lo == hi:
        return _to_float_point(start)

    end = (p1[0] + hi * d1x, p1[1] + hi * d1y)
    return (_to_float_point(start), _to_float_point(end))