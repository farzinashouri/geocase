"""Exact intersection of two 2D line segments.

segment_intersection(a, b) returns:
  * None                         if the segments share no point,
  * (x, y)                       if they share exactly one point,
  * ((xa, ya), (xb, yb))         if they overlap along a sub-segment.

Coordinates are floats; computations use a small relative tolerance so that
touching/collinear cases produced by floating-point arithmetic are handled.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple, Union

Point = Tuple[float, float]
Segment = Tuple[Point, Point]
Result = Union[None, Point, Segment]

_REL_EPS = 1e-12


def _scale(a: Segment, b: Segment) -> float:
    """Characteristic magnitude of the input for relative tolerances."""
    m = 0.0
    for seg in (a, b):
        for p in seg:
            m = max(m, abs(float(p[0])), abs(float(p[1])))
    return m if m > 0.0 else 1.0


def _cross(ox: float, oy: float, ax: float, ay: float, bx: float, by: float) -> float:
    """Cross product of (a - o) x (b - o)."""
    return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox)


def _param_along(p0: Point, d: Point, q: Point) -> float:
    """Scalar t such that q ~= p0 + t*d, for q collinear with the line."""
    dx, dy = d
    if abs(dx) >= abs(dy):
        return (q[0] - p0[0]) / dx
    return (q[1] - p0[1]) / dy


def segment_intersection(a: Segment, b: Segment) -> Result:
    (ax1, ay1), (ax2, ay2) = ((float(a[0][0]), float(a[0][1])),
                              (float(a[1][0]), float(a[1][1])))
    (bx1, by1), (bx2, by2) = ((float(b[0][0]), float(b[0][1])),
                              (float(b[1][0]), float(b[1][1])))

    scale = _scale(a, b)
    eps = _REL_EPS * scale            # length tolerance
    eps2 = eps * scale                # area (cross product) tolerance

    p = (ax1, ay1)
    r = (ax2 - ax1, ay2 - ay1)
    q = (bx1, by1)
    s = (bx2 - bx1, by2 - by1)

    a_degenerate = math.hypot(*r) <= eps
    b_degenerate = math.hypot(*s) <= eps

    # ---- Degenerate (point) segments -------------------------------------
    if a_degenerate and b_degenerate:
        if math.hypot(ax1 - bx1, ay1 - by1) <= eps:
            return (ax1, ay1)
        return None
    if a_degenerate:
        return _point_on_segment((ax1, ay1), b, eps, eps2)
    if b_degenerate:
        return _point_on_segment((bx1, by1), a, eps, eps2)

    rxs = r[0] * s[1] - r[1] * s[0]
    qp = (q[0] - p[0], q[1] - p[1])
    qpxr = qp[0] * r[1] - qp[1] * r[0]

    # ---- Parallel case -----------------------------------------------------
    if abs(rxs) <= eps2:
        if abs(qpxr) > eps2:
            return None  # parallel, non-collinear

        # Collinear: project b's endpoints onto a's parametrisation.
        t0 = _param_along(p, r, (bx1, by1))
        t1 = _param_along(p, r, (bx2, by2))
        lo, hi = (t0, t1) if t0 <= t1 else (t1, t0)
        # Tolerance in parameter space.
        r_len = math.hypot(*r)
        teps = eps / r_len
        lo_c = max(lo, 0.0)
        hi_c = min(hi, 1.0)
        if lo_c > hi_c + teps:
            return None
        if abs(hi_c - lo_c) <= teps:
            t = 0.5 * (lo_c + hi_c)
            return _snap_point(p, r, t, a, b, eps)
        pa = _snap_point(p, r, lo_c, a, b, eps)
        pb = _snap_point(p, r, hi_c, a, b, eps)
        return (pa, pb)

    # ---- Proper (non-parallel) case -----------------------------------------
    qpxs = qp[0] * s[1] - qp[1] * s[0]
    t = qpxs / rxs
    u = qpxr / rxs

    r_len = math.hypot(*r)
    s_len = math.hypot(*s)
    teps = eps / r_len
    ueps = eps / s_len

    if t < -teps or t > 1.0 + teps or u < -ueps or u > 1.0 + ueps:
        return None

    t = min(1.0, max(0.0, t))
    return _snap_point(p, r, t, a, b, eps)


def _point_on_segment(pt: Point, seg: Segment, eps: float, eps2: float) -> Optional[Point]:
    """Return pt if it lies on seg (within tolerance), else None."""
    (x1, y1), (x2, y2) = seg
    x1, y1, x2, y2 = float(x1), float(y1), float(x2), float(y2)
    d = (x2 - x1, y2 - y1)
    seg_len = math.hypot(*d)
    if seg_len <= eps:
        if math.hypot(pt[0] - x1, pt[1] - y1) <= eps:
            return (x1, y1)
        return None
    # Perpendicular distance via cross product / length.
    cr = _cross(x1, y1, x2, y2, pt[0], pt[1])
    if abs(cr) / seg_len > eps:
        return None
    t = _param_along((x1, y1), d, pt)
    teps = eps / seg_len
    if t < -teps or t > 1.0 + teps:
        return None
    return pt


def _snap_point(p: Point, r: Point, t: float, a: Segment, b: Segment, eps: float) -> Point:
    """Compute p + t*r and snap to an original endpoint if within tolerance.

    Snapping ensures that intersections at shared vertices return the exact
    input coordinates rather than values perturbed by rounding.
    """
    x = p[0] + t * r[0]
    y = p[1] + t * r[1]
    best = None
    best_d = eps
    for seg in (a, b):
        for ex, ey in seg:
            ex, ey = float(ex), float(ey)
            d = math.hypot(x - ex, y - ey)
            if d <= best_d:
                best, best_d = (ex, ey), d
    return best if best is not None else (x, y)


__all__ = ["segment_intersection"]