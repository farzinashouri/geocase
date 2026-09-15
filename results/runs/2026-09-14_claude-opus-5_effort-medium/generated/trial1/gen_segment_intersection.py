"""Exact-as-practical intersection of two planar line segments.

The module is dependency-free (standard library only) and has no import-time
side effects.

    >>> segment_intersection(((0.0, 0.0), (2.0, 2.0)), ((0.0, 2.0), (2.0, 0.0)))
    (1.0, 1.0)

The result of :func:`segment_intersection` is

* ``None``                      -- the segments share no point,
* ``(x, y)``                    -- they share exactly one point,
* ``((xa, ya), (xb, yb))``      -- they share a sub-segment (collinear overlap).

Degenerate (zero-length) segments are accepted and treated as points.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple, Union

Point = Tuple[float, float]
Segment = Tuple[Point, Point]
Result = Union[None, Point, Segment]

__all__ = ["segment_intersection", "Point", "Segment", "Result"]

# Relative tolerance used for every degeneracy test.  All comparisons are
# scaled by the magnitudes of the quantities involved, so the function behaves
# the same for coordinates in metres, in degrees, or in projected megametres.
_REL_EPS = 1e-12


def _sub(p: Point, q: Point) -> Point:
    return (p[0] - q[0], p[1] - q[1])


def _cross(u: Point, v: Point) -> float:
    return u[0] * v[1] - u[1] * v[0]


def _dot(u: Point, v: Point) -> float:
    return u[0] * v[0] + u[1] * v[1]


def _norm(u: Point) -> float:
    return math.hypot(u[0], u[1])


def _check(seg, name: str) -> Segment:
    try:
        (x1, y1), (x2, y2) = seg
        p0 = (float(x1), float(y1))
        p1 = (float(x2), float(y2))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{name} must be a pair of (x, y) coordinate pairs, got {seg!r}"
        ) from exc
    for x, y in (p0, p1):
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError(f"{name} has a non-finite coordinate: {seg!r}")
    return (p0, p1)


def _point_on_segment(pt: Point, seg: Segment) -> bool:
    """True if ``pt`` lies on ``seg`` (which may itself be degenerate)."""
    s0, s1 = seg
    d = _sub(s1, s0)
    w = _sub(pt, s0)
    len_d = _norm(d)
    if len_d == 0.0:
        # Degenerate segment: it is a point.
        scale = max(_norm(pt), _norm(s0), 1.0)
        return _norm(w) <= _REL_EPS * scale
    # Off-line distance, expressed as twice the triangle area.
    if abs(_cross(d, w)) > _REL_EPS * len_d * max(len_d, _norm(w)):
        return False
    t = _dot(w, d) / _dot(d, d)
    return -_REL_EPS <= t <= 1.0 + _REL_EPS


def _at(seg: Segment, t: float) -> Point:
    """Point at parameter ``t`` along ``seg``, snapping the exact endpoints."""
    p0, p1 = seg
    if t <= 0.0:
        return p0
    if t >= 1.0:
        return p1
    return (p0[0] + t * (p1[0] - p0[0]), p0[1] + t * (p1[1] - p0[1]))


def _collinear_overlap(a: Segment, b: Segment) -> Result:
    """Shared portion of two segments already known to be collinear."""
    p, r = a[0], _sub(a[1], a[0])
    rr = _dot(r, r)

    # Parameters of b's endpoints along a.
    tb0 = _dot(_sub(b[0], p), r) / rr
    tb1 = _dot(_sub(b[1], p), r) / rr
    lo_b, hi_b = ((tb0, b[0]), (tb1, b[1])) if tb0 <= tb1 else ((tb1, b[1]), (tb0, b[0]))

    lo = max((0.0, a[0]), lo_b, key=lambda item: item[0])
    hi = min((1.0, a[1]), hi_b, key=lambda item: item[0])

    length = _norm(r)
    tol = _REL_EPS * max(length, _norm(_sub(b[1], b[0])))
    overlap = (hi[0] - lo[0]) * length

    if overlap < -tol:
        return None
    if overlap <= tol:
        # The segments touch at a single (endpoint) point.
        return _at(a, min(max(lo[0], 0.0), 1.0))
    return (lo[1], hi[1])


def segment_intersection(a: Segment, b: Segment) -> Result:
    """Intersect the 2D segments ``a`` and ``b``.

    Parameters
    ----------
    a, b:
        Segments given as ``((x1, y1), (x2, y2))`` with float coordinates in a
        planar (Cartesian) system.  Zero-length segments are allowed and are
        treated as points.

    Returns
    -------
    ``None`` when the segments are disjoint, ``(x, y)`` when they meet in
    exactly one point, or ``((xa, ya), (xb, yb))`` when they overlap along a
    sub-segment.  For an overlap the endpoints are ordered along ``a``.

    Raises
    ------
    ValueError
        If an argument is not a pair of coordinate pairs, or holds a NaN or
        infinite coordinate.
    """
    a = _check(a, "a")
    b = _check(b, "b")

    r = _sub(a[1], a[0])
    s = _sub(b[1], b[0])
    len_r, len_s = _norm(r), _norm(s)

    # --- degenerate inputs -------------------------------------------------
    if len_r == 0.0 and len_s == 0.0:
        scale = max(_norm(a[0]), _norm(b[0]), 1.0)
        if _norm(_sub(a[0], b[0])) <= _REL_EPS * scale:
            return a[0]
        return None
    if len_r == 0.0:
        return a[0] if _point_on_segment(a[0], b) else None
    if len_s == 0.0:
        return b[0] if _point_on_segment(b[0], a) else None

    # --- general case ------------------------------------------------------
    denom = _cross(r, s)
    qp = _sub(b[0], a[0])

    # Treat as parallel when the cross product is negligible relative to the
    # segment lengths; otherwise the t/u division below is numerically junk.
    if abs(denom) <= _REL_EPS * len_r * len_s:
        # Parallel: collinear only if b[0] lies on a's supporting line.
        if abs(_cross(qp, r)) > _REL_EPS * len_r * max(len_r, _norm(qp)):
            return None
        return _collinear_overlap(a, b)

    t = _cross(qp, s) / denom
    u = _cross(qp, r) / denom
    if not (-_REL_EPS <= t <= 1.0 + _REL_EPS):
        return None
    if not (-_REL_EPS <= u <= 1.0 + _REL_EPS):
        return None
    return _at(a, min(max(t, 0.0), 1.0))