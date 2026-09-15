"""Segment-segment intersection for 2D line segments with float coordinates."""

from typing import Optional, Tuple, Union

Point = Tuple[float, float]
Segment = Tuple[Point, Point]


def _sub(p: Point, q: Point) -> Point:
    return (p[0] - q[0], p[1] - q[1])


def _cross(v: Point, w: Point) -> float:
    return v[0] * w[1] - v[1] * w[0]


def _dot(v: Point, w: Point) -> float:
    return v[0] * w[0] + v[1] * w[1]


def _point_on_segment(pt: Point, seg: Segment) -> bool:
    s0, s1 = seg
    d = _sub(s1, s0)
    dp = _sub(pt, s0)
    if _cross(d, dp) != 0:
        return False
    dd = _dot(d, d)
    if dd == 0:
        return pt == s0
    t = _dot(dp, d) / dd
    return 0 <= t <= 1


def segment_intersection(
    a: Segment, b: Segment
) -> Optional[Union[Point, Segment]]:
    """Return the intersection of two 2D segments.

    Returns None for no overlap, a point (x, y) for a single shared
    point, or a segment ((xa, ya), (xb, yb)) for a shared sub-segment.
    """
    a0, a1 = a
    b0, b1 = b

    a_is_point = a0 == a1
    b_is_point = b0 == b1

    if a_is_point and b_is_point:
        return a0 if a0 == b0 else None
    if a_is_point:
        return a0 if _point_on_segment(a0, b) else None
    if b_is_point:
        return b0 if _point_on_segment(b0, a) else None

    r = _sub(a1, a0)
    s = _sub(b1, b0)
    rxs = _cross(r, s)
    qmp = _sub(b0, a0)
    qmpxr = _cross(qmp, r)

    if rxs == 0:
        if qmpxr != 0:
            return None  # parallel, non-collinear

        # Collinear: find overlap of the two parameter intervals along r.
        rr = _dot(r, r)
        t0 = _dot(qmp, r) / rr
        t1 = t0 + _dot(s, r) / rr
        tmin, tmax = (t0, t1) if t0 <= t1 else (t1, t0)

        lo = max(0.0, tmin)
        hi = min(1.0, tmax)
        if lo > hi:
            return None

        p_lo = (a0[0] + lo * r[0], a0[1] + lo * r[1])
        if lo == hi:
            return p_lo
        p_hi = (a0[0] + hi * r[0], a0[1] + hi * r[1])
        return (p_lo, p_hi)

    t = _cross(qmp, s) / rxs
    u = qmpxr / rxs
    if 0 <= t <= 1 and 0 <= u <= 1:
        return (a0[0] + t * r[0], a0[1] + t * r[1])
    return None