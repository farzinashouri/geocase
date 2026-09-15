"""Planar segment–segment intersection.

Computes the exact set-theoretic intersection of two 2D line segments and
reports it as ``None`` (disjoint), a point (single common point), or a
segment (a shared collinear portion).

Pure standard library; importing this module has no side effects.

Example
-------
>>> segment_intersection(((0.0, 0.0), (2.0, 2.0)), ((0.0, 2.0), (2.0, 0.0)))
(1.0, 1.0)
>>> segment_intersection(((0.0, 0.0), (2.0, 0.0)), ((1.0, 0.0), (3.0, 0.0)))
((1.0, 0.0), (2.0, 0.0))
>>> segment_intersection(((0.0, 0.0), (1.0, 0.0)), ((0.0, 1.0), (1.0, 1.0))) is None
True
"""

from __future__ import annotations

import math
from typing import Optional, Tuple, Union

__all__ = ["segment_intersection"]

Point = Tuple[float, float]
Segment = Tuple[Point, Point]
Result = Optional[Union[Point, Segment]]

# Relative tolerance applied to the coordinate magnitude of the inputs.  All
# comparisons below are expressed as distances so that this single knob has a
# geometric meaning: two features closer than ``_REL_EPS * scale`` are treated
# as touching.
_REL_EPS = 1e-12


def _as_point(p) -> Point:
    x, y = p
    x = float(x)
    y = float(y)
    if not (math.isfinite(x) and math.isfinite(y)):
        raise ValueError(f"non-finite coordinate in point {p!r}")
    return (x, y)


def _as_segment(s) -> Segment:
    p, q = s
    return (_as_point(p), _as_point(q))


def _tolerance(*pts: Point) -> float:
    """Absolute distance tolerance scaled to the magnitude of the inputs."""
    scale = 1.0
    for x, y in pts:
        scale = max(scale, abs(x), abs(y))
    return _REL_EPS * scale


def _cross(ox: float, oy: float, ax: float, ay: float, bx: float, by: float) -> float:
    """Cross product of (a - o) x (b - o)."""
    return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox)


def _lerp(p: Point, q: Point, t: float) -> Point:
    """Point at parameter ``t`` along p->q, snapping exactly at the ends."""
    if t <= 0.0:
        return p
    if t >= 1.0:
        return q
    return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))


def _dist(p: Point, q: Point) -> float:
    return math.hypot(q[0] - p[0], q[1] - p[1])


def _point_on_segment(p: Point, s: Segment, tol: float) -> bool:
    """True if ``p`` lies within ``tol`` of segment ``s`` (endpoints included)."""
    (x1, y1), (x2, y2) = s
    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq == 0.0:  # degenerate segment: a point
        return _dist(p, s[0]) <= tol
    # Perpendicular distance from the supporting line.
    if abs(_cross(x1, y1, x2, y2, p[0], p[1])) > tol * math.sqrt(length_sq):
        return False
    # Inside the slab spanned by the endpoints (with tolerance).
    t = ((p[0] - x1) * dx + (p[1] - y1) * dy) / length_sq
    t_tol = tol / math.sqrt(length_sq)
    return -t_tol <= t <= 1.0 + t_tol


def _collapse(p: Point, q: Point, tol: float) -> Result:
    """Report a degenerate overlap as a point rather than a zero-length segment."""
    if _dist(p, q) <= tol:
        return p
    return (p, q)


def _collinear_overlap(a: Segment, b: Segment, tol: float) -> Result:
    """Intersection of two collinear segments, both known to be non-degenerate."""
    (ax1, ay1), (ax2, ay2) = a
    dx = ax2 - ax1
    dy = ay2 - ay1
    length_sq = dx * dx + dy * dy

    def param(p: Point) -> float:
        return ((p[0] - ax1) * dx + (p[1] - ay1) * dy) / length_sq

    t0 = param(b[0])
    t1 = param(b[1])
    if t0 > t1:
        t0, t1 = t1, t0

    t_tol = tol / math.sqrt(length_sq)
    lo = max(0.0, t0)
    hi = min(1.0, t1)
    if lo > hi + t_tol:
        return None
    if lo > hi:  # within tolerance: a single touching point
        lo = hi = 0.5 * (lo + hi)
    return _collapse(_lerp(a[0], a[1], lo), _lerp(a[0], a[1], hi), tol)


def segment_intersection(a: Segment, b: Segment) -> Result:
    """Intersect two planar line segments.

    Parameters
    ----------
    a, b:
        Segments given as ``((x1, y1), (x2, y2))`` with float coordinates in a
        planar (projected) coordinate system.  Degenerate (zero-length)
        segments are accepted and treated as points.

    Returns
    -------
    ``None``
        if the segments share no point;
    ``(x, y)``
        if they share exactly one point;
    ``((xa, ya), (xb, yb))``
        if they overlap in more than one point, giving the endpoints of the
        shared collinear portion (ordered along ``a``).
    """
    a = _as_segment(a)
    b = _as_segment(b)
    tol = _tolerance(a[0], a[1], b[0], b[1])

    a_is_point = _dist(a[0], a[1]) <= tol
    b_is_point = _dist(b[0], b[1]) <= tol

    # --- degenerate inputs -------------------------------------------------
    if a_is_point and b_is_point:
        return a[0] if _dist(a[0], b[0]) <= tol else None
    if a_is_point:
        return a[0] if _point_on_segment(a[0], b, tol) else None
    if b_is_point:
        return b[0] if _point_on_segment(b[0], a, tol) else None

    (ax1, ay1), (ax2, ay2) = a
    (bx1, by1), (bx2, by2) = b
    rx, ry = ax2 - ax1, ay2 - ay1
    sx, sy = bx2 - bx1, by2 - by1

    r_len = math.hypot(rx, ry)
    s_len = math.hypot(sx, sy)
    denom = rx * sy - ry * sx

    # Parallel (or numerically indistinguishable from parallel): the segments
    # either lie on a common line or never meet.
    if abs(denom) <= tol * r_len * s_len:
        # Distance of b's endpoints from a's supporting line.
        off1 = abs(_cross(ax1, ay1, ax2, ay2, bx1, by1)) / r_len
        off2 = abs(_cross(ax1, ay1, ax2, ay2, bx2, by2)) / r_len
        if off1 > tol or off2 > tol:
            return None
        return _collinear_overlap(a, b, tol)

    # --- general (crossing) case ------------------------------------------
    qpx, qpy = bx1 - ax1, by1 - ay1
    t = (qpx * sy - qpy * sx) / denom
    u = (qpx * ry - qpy * rx) / denom

    # Parameter tolerances corresponding to the distance tolerance.
    if not (-tol / r_len <= t <= 1.0 + tol / r_len):
        return None
    if not (-tol / s_len <= u <= 1.0 + u * 0.0 + tol / s_len):
        return None

    return _lerp(a[0], a[1], min(1.0, max(0.0, t)))