"""Exact intersection of two 2D line segments.

The public entry point is :func:`segment_intersection`. All arithmetic is
carried out with :class:`fractions.Fraction` so that the float inputs are
handled exactly; results are converted back to ``float`` on return.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Optional, Tuple, Union

Point = Tuple[float, float]
Segment = Tuple[Point, Point]
Result = Union[None, Point, Segment]

_FPoint = Tuple[Fraction, Fraction]


def _to_fraction_point(p) -> _FPoint:
    x, y = p
    return Fraction(x), Fraction(y)


def _sub(p: _FPoint, q: _FPoint) -> _FPoint:
    return p[0] - q[0], p[1] - q[1]


def _cross(p: _FPoint, q: _FPoint) -> Fraction:
    return p[0] * q[1] - p[1] * q[0]


def _dot(p: _FPoint, q: _FPoint) -> Fraction:
    return p[0] * q[0] + p[1] * q[1]


def _is_zero(v: _FPoint) -> bool:
    return v[0] == 0 and v[1] == 0


def _point_at(p: _FPoint, r: _FPoint, t: Fraction) -> Point:
    return float(p[0] + t * r[0]), float(p[1] + t * r[1])


def segment_intersection(a: Segment, b: Segment) -> Result:
    """Return the intersection of two closed 2D line segments.

    Each segment is ``((x1, y1), (x2, y2))``. Degenerate segments (both
    endpoints equal) are treated as points.

    Returns
    -------
    ``None``
        The segments share no point.
    ``(x, y)``
        The segments share exactly one point.
    ``((xa, ya), (xb, yb))``
        The segments share a positive-length portion; the tuple gives its
        endpoints ordered along the direction of segment ``a`` (or ``b`` if
        ``a`` is degenerate).
    """
    p = _to_fraction_point(a[0])
    r = _sub(_to_fraction_point(a[1]), p)
    q = _to_fraction_point(b[0])
    s = _sub(_to_fraction_point(b[1]), q)

    # Make sure the "reference" segment (p, r) is non-degenerate if either is.
    if _is_zero(r) and not _is_zero(s):
        p, r, q, s = q, s, p, r

    # Both segments are single points.
    if _is_zero(r):
        return (float(p[0]), float(p[1])) if p == q else None

    qp = _sub(q, p)
    r_cross_s = _cross(r, s)
    qp_cross_r = _cross(qp, r)

    if r_cross_s == 0:
        if qp_cross_r != 0:
            # Parallel (or a point off the line) and not collinear.
            return None

        # Collinear: project b's endpoints onto a's parameter space.
        rr = _dot(r, r)
        t0 = _dot(qp, r) / rr
        t1 = t0 + _dot(s, r) / rr
        lo = max(Fraction(0), min(t0, t1))
        hi = min(Fraction(1), max(t0, t1))

        if lo > hi:
            return None
        if lo == hi:
            return _point_at(p, r, lo)
        return _point_at(p, r, lo), _point_at(p, r, hi)

    # Non-parallel lines: solve p + t*r = q + u*s.
    t = _cross(qp, s) / r_cross_s
    u = qp_cross_r / r_cross_s
    if 0 <= t <= 1 and 0 <= u <= 1:
        return _point_at(p, r, t)
    return None


__all__ = ["segment_intersection"]