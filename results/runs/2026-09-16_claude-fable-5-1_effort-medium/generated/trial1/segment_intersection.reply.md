```python
"""Exact-ish intersection of two 2D line segments.

segment_intersection(a, b) -> None | (x, y) | ((xa, ya), (xb, yb))
"""

from __future__ import annotations

from typing import Optional, Tuple, Union

Point = Tuple[float, float]
Segment = Tuple[Point, Point]
Result = Union[None, Point, Segment]

_REL_EPS = 1e-12


def _cross(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * by - ay * bx


def _scale(a: Segment, b: Segment) -> float:
    m = 1.0
    for seg in (a, b):
        for p in seg:
            m = max(m, abs(p[0]), abs(p[1]))
    return m


def _same(p: Point, q: Point, eps: float) -> bool:
    return abs(p[0] - q[0]) <= eps and abs(p[1] - q[1]) <= eps


def _point_on_segment(p: Point, s: Segment, eps: float) -> bool:
    (x1, y1), (x2, y2) = s
    px, py = p
    if abs(_cross(x2 - x1, y2 - y1, px - x1, py - y1)) > eps * max(1.0, abs(x2 - x1) + abs(y2 - y1)):
        return False
    return (
        min(x1, x2) - eps <= px <= max(x1, x2) + eps
        and min(y1, y2) - eps <= py <= max(y1, y2) + eps
    )


def _collinear_overlap(a: Segment, b: Segment, eps: float) -> Result:
    """Both segments lie on one line; a is non-degenerate. Return overlap."""
    (ax1, ay1), (ax2, ay2) = a
    dx, dy = ax2 - ax1, ay2 - ay1
    length2 = dx * dx + dy * dy

    def param(p: Point) -> float:
        return ((p[0] - ax1) * dx + (p[1] - ay1) * dy) / length2

    def at(t: float) -> Point:
        return (ax1 + t * dx, ay1 + t * dy)

    tb1, tb2 = param(b[0]), param(b[1])
    lo, hi = max(0.0, min(tb1, tb2)), min(1.0, max(tb1, tb2))
    teps = eps / (length2 ** 0.5)
    if lo > hi + teps:
        return None
    if hi - lo <= teps:
        return at(0.5 * (lo + hi))
    return (at(lo), at(hi))


def segment_intersection(a: Segment, b: Segment) -> Result:
    """Intersect two segments ((x1, y1), (x2, y2)).

    Returns None (disjoint), a point (single shared point), or a segment
    (shared portion with positive length).
    """
    a = ((float(a[0][0]), float(a[0][1])), (float(a[1][0]), float(a[1][1])))
    b = ((float(b[0][0]), float(b[0][1])), (float(b[1][0]), float(b[1][1])))
    eps = _REL_EPS * _scale(a, b)

    a_degenerate = _same(a[0], a[1], eps)
    b_degenerate = _same(b[0], b[1], eps)

    if a_degenerate and b_degenerate:
        return a[0] if _same(a[0], b[0], eps) else None
    if a_degenerate:
        return a[0] if _point_on_segment(a[0], b, eps) else None
    if b_degenerate:
        return b[0] if _point_on_segment(b[0], a, eps) else None

    (px, py), (px2, py2) = a
    (qx, qy), (qx2, qy2) = b
    rx, ry = px2 - px, py2 - py
    sx, sy = qx2 - qx, qy2 - qy
    qpx, qpy = qx - px, qy - py

    denom = _cross(rx, ry, sx, sy)
    qp_r = _cross(qpx, qpy, rx, ry)
    area_eps = eps * max(1.0, abs(rx) + abs(ry) + abs(sx) + abs(sy))

    if abs(denom) <= area_eps:
        if abs(qp_r) <= area_eps:
            return _collinear_overlap(a, b, eps)
        return None

    t = _cross(qpx, qpy, sx, sy) / denom
    u = qp_r / denom
    teps = eps / max(abs(rx), abs(ry))
    ueps = eps / max(abs(sx), abs(sy))
    if -teps <= t <= 1.0 + teps and -ueps <= u <= 1.0 + ueps:
        t = min(1.0, max(0.0, t))
        return (px + t * rx, py + t * ry)
    return None
```