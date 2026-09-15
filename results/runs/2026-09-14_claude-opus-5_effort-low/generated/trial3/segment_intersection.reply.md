```python
"""Planar segment–segment intersection.

Pure-Python, no side effects on import.

A segment is a pair of endpoints ``((x1, y1), (x2, y2))`` with float
coordinates in a planar (Cartesian) coordinate system.  Degenerate
segments whose endpoints coincide are accepted and treated as points.
"""

from __future__ import annotations

__all__ = ["segment_intersection"]

# Relative tolerance used for all "is this zero?" decisions.  Comparisons are
# scaled by the magnitudes of the operands so the predicate behaves the same
# for coordinates in metres and in degrees.
_REL_EPS = 1e-12


def _cross(ox, oy, ax, ay, bx, by):
    """2D cross product of (a - o) x (b - o)."""
    return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox)


def _scale(*coords):
    """Magnitude scale of the inputs, never below 1.0."""
    return max(1.0, max(abs(c) for c in coords))


def segment_intersection(a, b):
    """Return the intersection of two 2D segments.

    Returns ``None`` when the segments share no point, ``(x, y)`` when they
    share exactly one point, and ``((xa, ya), (xb, yb))`` when they share a
    sub-segment (the endpoints of the shared portion).
    """
    (p1x, p1y), (p2x, p2y) = ((float(a[0][0]), float(a[0][1])),
                              (float(a[1][0]), float(a[1][1])))
    (q1x, q1y), (q2x, q2y) = ((float(b[0][0]), float(b[0][1])),
                              (float(b[1][0]), float(b[1][1])))

    rx, ry = p2x - p1x, p2y - p1y
    sx, sy = q2x - q1x, q2y - q1y

    scale = _scale(p1x, p1y, p2x, p2y, q1x, q1y, q2x, q2y)
    eps = _REL_EPS * scale

    a_is_point = abs(rx) <= eps and abs(ry) <= eps
    b_is_point = abs(sx) <= eps and abs(sy) <= eps

    if a_is_point and b_is_point:
        if abs(p1x - q1x) <= eps and abs(p1y - q1y) <= eps:
            return (p1x, p1y)
        return None
    if a_is_point:
        if _point_on_segment(p1x, p1y, q1x, q1y, sx, sy, eps):
            return (p1x, p1y)
        return None
    if b_is_point:
        if _point_on_segment(q1x, q1y, p1x, p1y, rx, ry, eps):
            return (q1x, q1y)
        return None

    denom = rx * sy - ry * sx
    # Parallelism test scaled by the segment lengths: |r x s| = |r||s|sin(t).
    len_r = (rx * rx + ry * ry) ** 0.5
    len_s = (sx * sx + sy * sy) ** 0.5

    if abs(denom) > _REL_EPS * len_r * len_s:
        qpx, qpy = q1x - p1x, q1y - p1y
        t = (qpx * sy - qpy * sx) / denom
        u = (qpx * ry - qpy * rx) / denom
        # Parameter tolerances scale back to a distance tolerance on each line.
        t_eps = eps / len_r
        u_eps = eps / len_s
        if -t_eps <= t <= 1.0 + t_eps and -u_eps <= u <= 1.0 + u_eps:
            t = min(1.0, max(0.0, t))
            return (p1x + t * rx, p1y + t * ry)
        return None

    # Parallel: collinear only if b's start lies on a's supporting line.
    if abs(_cross(p1x, p1y, p2x, p2y, q1x, q1y)) > eps * len_r:
        return None

    # Collinear — compare the two overlapping parameter intervals along r.
    rr = rx * rx + ry * ry
    t0 = ((q1x - p1x) * rx + (q1y - p1y) * ry) / rr
    t1 = ((q2x - p1x) * rx + (q2y - p1y) * ry) / rr
    if t0 > t1:
        t0, t1 = t1, t0

    lo = max(0.0, t0)
    hi = min(1.0, t1)
    t_eps = eps / len_r

    if lo > hi + t_eps:
        return None
    if hi - lo <= t_eps:
        t = min(1.0, max(0.0, 0.5 * (lo + hi)))
        return (p1x + t * rx, p1y + t * ry)

    return ((p1x + lo * rx, p1y + lo * ry),
            (p1x + hi * rx, p1y + hi * ry))


def _point_on_segment(px, py, ax, ay, dx, dy, eps):
    """True if (px, py) lies on the segment starting at (ax, ay) with direction (dx, dy)."""
    length = (dx * dx + dy * dy) ** 0.5
    if abs((px - ax) * dy - (py - ay) * dx) > eps * length:
        return False
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t_eps = eps / length
    return -t_eps <= t <= 1.0 + t_eps
```