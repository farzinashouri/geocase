Here is the module.

```python
"""Intersection of two 2D line segments.

``segment_intersection(a, b)`` returns ``None`` when the segments share no
point, a point ``(x, y)`` when they share exactly one point, and a segment
``((xa, ya), (xb, yb))`` when they share more than one point (collinear
overlap). Coordinates are floats in a planar system; comparisons use a small
tolerance scaled to the magnitude of the input coordinates.
"""

from __future__ import annotations

from math import hypot
from typing import Optional, Tuple, Union

__all__ = ["segment_intersection"]

Point = Tuple[float, float]
Segment = Tuple[Point, Point]

_REL_EPS = 1e-9


def _as_point(p) -> Point:
    return (float(p[0]), float(p[1]))


def _cross(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * by - ay * bx


def _dot(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * bx + ay * by


def _scale(*pts: Point) -> float:
    m = max(abs(c) for p in pts for c in p)
    return m if m > 0.0 else 1.0


def _same_point(p: Point, q: Point, tol: float) -> bool:
    return hypot(p[0] - q[0], p[1] - q[1]) <= tol


def _on_segment(pt: Point, s1: Point, s2: Point, tol: float) -> bool:
    """True if ``pt`` lies within ``tol`` of the (non-degenerate) segment s1-s2."""
    dx, dy = s2[0] - s1[0], s2[1] - s1[1]
    wx, wy = pt[0] - s1[0], pt[1] - s1[1]
    dd = _dot(dx, dy, dx, dy)
    t = _dot(wx, wy, dx, dy) / dd
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    cx, cy = s1[0] + t * dx, s1[1] + t * dy
    return hypot(pt[0] - cx, pt[1] - cy) <= tol


def _snap(pt: Point, candidates, tol: float) -> Point:
    """Replace ``pt`` by an original endpoint if one is within ``tol``."""
    for c in candidates:
        if _same_point(pt, c, tol):
            return c
    return pt


def segment_intersection(a: Segment, b: Segment) -> Union[None, Point, Segment]:
    p1, p2 = _as_point(a[0]), _as_point(a[1])
    q1, q2 = _as_point(b[0]), _as_point(b[1])

    tol = _REL_EPS * _scale(p1, p2, q1, q2)

    rx, ry = p2[0] - p1[0], p2[1] - p1[1]
    sx, sy = q2[0] - q1[0], q2[1] - q1[1]
    r_len = hypot(rx, ry)
    s_len = hypot(sx, sy)

    a_is_point = r_len <= tol
    b_is_point = s_len <= tol

    # Degenerate inputs: one or both segments collapse to a point.
    if a_is_point and b_is_point:
        return p1 if _same_point(p1, q1, tol) else None
    if a_is_point:
        return _snap(p1, (q1, q2), tol) if _on_segment(p1, q1, q2, tol) else None
    if b_is_point:
        return _snap(q1, (p1, p2), tol) if _on_segment(q1, p1, p2, tol) else None

    wx, wy = q1[0] - p1[0], q1[1] - p1[1]
    denom = _cross(rx, ry, sx, sy)

    # Parallel test: |denom| = |r||s||sin(theta)|.
    if abs(denom) <= _REL_EPS * r_len * s_len:
        # Parallel. Collinear only if q1 lies on the line through a.
        dist_q1 = abs(_cross(wx, wy, rx, ry)) / r_len
        if dist_q1 > tol:
            return None

        # Parametrise everything along a: p1 -> t=0, p2 -> t=1.
        rr = r_len * r_len
        t0 = _dot(wx, wy, rx, ry) / rr
        t1 = t0 + _dot(sx, sy, rx, ry) / rr
        if t0 <= t1:
            b_lo, b_hi = (t0, q1), (t1, q2)
        else:
            b_lo, b_hi = (t1, q2), (t0, q1)

        lo = b_lo if b_lo[0] > 0.0 else (0.0, p1)
        hi = b_hi if b_hi[0] < 1.0 else (1.0, p2)

        tol_t = tol / r_len
        if lo[0] > hi[0] + tol_t:
            return None
        if hi[0] - lo[0] <= tol_t:
            return lo[1]
        return (lo[1], hi[1])

    # Proper (non-parallel) case: solve p1 + t r = q1 + u s.
    t = _cross(wx, wy, sx, sy) / denom
    u = _cross(wx, wy, rx, ry) / denom

    tol_t = tol / r_len
    tol_u = tol / s_len
    if t < -tol_t or t > 1.0 + tol_t or u < -tol_u or u > 1.0 + tol_u:
        return None

    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    pt = (p1[0] + t * rx, p1[1] + t * ry)
    return _snap(pt, (p1, p2, q1, q2), tol)
```