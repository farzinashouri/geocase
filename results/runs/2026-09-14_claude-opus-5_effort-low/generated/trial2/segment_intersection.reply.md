```python
"""Planar line-segment intersection.

Computes the intersection of two 2D line segments, which may be empty, a
single point, or (for collinear overlapping segments) a sub-segment.

Pure standard library; importing this module has no side effects.
"""

from __future__ import annotations

Point = tuple[float, float]
Segment = tuple[Point, Point]

# Relative tolerance used to decide whether a quantity is zero.  All
# comparisons are scaled by the magnitude of the input coordinates so the
# function behaves the same for metre-scale and degree-scale data.
_REL_EPS = 1e-12


def _cross(ox: float, oy: float, ax: float, ay: float, bx: float, by: float) -> float:
    """Z-component of (a - o) x (b - o)."""
    return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox)


def _scale(*points: Point) -> float:
    """Largest absolute coordinate among ``points``, at least 1.0."""
    m = 1.0
    for x, y in points:
        m = max(m, abs(x), abs(y))
    return m


def _point_on_segment(p: Point, s: Segment, eps_area: float, eps_len: float) -> bool:
    """True if ``p`` lies on segment ``s`` (endpoints included)."""
    (x1, y1), (x2, y2) = s
    px, py = p
    if abs(_cross(x1, y1, x2, y2, px, py)) > eps_area:
        return False
    return (
        min(x1, x2) - eps_len <= px <= max(x1, x2) + eps_len
        and min(y1, y2) - eps_len <= py <= max(y1, y2) + eps_len
    )


def _same_point(p: Point, q: Point, eps_len: float) -> bool:
    return abs(p[0] - q[0]) <= eps_len and abs(p[1] - q[1]) <= eps_len


def segment_intersection(a: Segment, b: Segment):
    """Intersect two 2D segments.

    Each segment is ``((x1, y1), (x2, y2))``.  Returns ``None`` when the
    segments share no point, ``(x, y)`` when they share exactly one, and
    ``((xa, ya), (xb, yb))`` when they share a sub-segment.

    Zero-length segments are treated as the single point they describe.
    """
    (ax1, ay1), (ax2, ay2) = ((float(a[0][0]), float(a[0][1])),
                              (float(a[1][0]), float(a[1][1])))
    (bx1, by1), (bx2, by2) = ((float(b[0][0]), float(b[0][1])),
                              (float(b[1][0]), float(b[1][1])))

    scale = _scale((ax1, ay1), (ax2, ay2), (bx1, by1), (bx2, by2))
    eps_len = _REL_EPS * scale
    eps_area = _REL_EPS * scale * scale

    a_degenerate = _same_point((ax1, ay1), (ax2, ay2), eps_len)
    b_degenerate = _same_point((bx1, by1), (bx2, by2), eps_len)

    # Degenerate inputs: a "segment" that is really a point.
    if a_degenerate and b_degenerate:
        return (ax1, ay1) if _same_point((ax1, ay1), (bx1, by1), eps_len) else None
    if a_degenerate:
        p = (ax1, ay1)
        return p if _point_on_segment(p, ((bx1, by1), (bx2, by2)), eps_area, eps_len) else None
    if b_degenerate:
        p = (bx1, by1)
        return p if _point_on_segment(p, ((ax1, ay1), (ax2, ay2)), eps_area, eps_len) else None

    rx, ry = ax2 - ax1, ay2 - ay1
    sx, sy = bx2 - bx1, by2 - by1
    qpx, qpy = bx1 - ax1, by1 - ay1

    denom = rx * sy - ry * sx
    qp_cross_r = qpx * ry - qpy * rx  # cross(q - p, r), negated sign convention below

    if abs(denom) > eps_area:
        # Proper (non-parallel) case: solve p + t*r = q + u*s.
        t = (qpx * sy - qpy * sx) / denom
        u = (qpx * ry - qpy * rx) / denom
        # Tolerance on the parameters, expressed relative to each direction.
        len_r = max((rx * rx + ry * ry) ** 0.5, eps_len)
        len_s = max((sx * sx + sy * sy) ** 0.5, eps_len)
        t_eps = eps_len / len_r
        u_eps = eps_len / len_s
        if -t_eps <= t <= 1.0 + t_eps and -u_eps <= u <= 1.0 + u_eps:
            t = min(1.0, max(0.0, t))
            return (ax1 + t * rx, ay1 + t * ry)
        return None

    # Parallel segments.
    if abs(qp_cross_r) > eps_area:
        return None  # parallel but not collinear

    # Collinear: project b's endpoints onto a's parameter space.
    rr = rx * rx + ry * ry
    t0 = (qpx * rx + qpy * ry) / rr
    t1 = t0 + (sx * rx + sy * ry) / rr
    lo, hi = (t0, t1) if t0 <= t1 else (t1, t0)

    lo = max(lo, 0.0)
    hi = min(hi, 1.0)

    t_eps = eps_len / max(rr ** 0.5, eps_len)
    if lo > hi + t_eps:
        return None

    p_lo = (ax1 + lo * rx, ay1 + lo * ry)
    if hi - lo <= t_eps:
        return p_lo
    return (p_lo, (ax1 + hi * rx, ay1 + hi * ry))
```