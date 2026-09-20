"""Segment-segment intersection in 2D."""

from __future__ import annotations

from typing import Optional, Tuple

Point = Tuple[float, float]
Segment = Tuple[Point, Point]


def _sub(p: Point, q: Point) -> Point:
    return (p[0] - q[0], p[1] - q[1])


def _cross(p: Point, q: Point) -> float:
    return p[0] * q[1] - p[1] * q[0]


def _on_segment(p: Point, seg: Segment) -> bool:
    (x1, y1), (x2, y2) = seg
    return (
        min(x1, x2) - 1e-12 <= p[0] <= max(x1, x2) + 1e-12
        and min(y1, y2) - 1e-12 <= p[1] <= max(y1, y2) + 1e-12
    )


def segment_intersection(
    a: Segment, b: Segment
) -> Optional[object]:
    (p, p2) = a
    (q, q2) = b
    r = _sub(p2, p)
    s = _sub(q2, q)
    rxs = _cross(r, s)
    qmp = _sub(q, p)
    qmpxr = _cross(qmp, r)

    eps = 1e-12

    if abs(rxs) < eps and abs(qmpxr) < eps:
        # Collinear: project onto the line direction to find overlap.
        rr = r[0] * r[0] + r[1] * r[1]
        if rr < eps:
            # 'a' is a point; check if it lies on 'b'.
            if _on_segment(p, b) and abs(_cross(_sub(p, q), s)) < eps:
                return p
            return None
        t0 = (qmp[0] * r[0] + qmp[1] * r[1]) / rr
        qq2mp = _sub(q2, p)
        t1 = (qq2mp[0] * r[0] + qq2mp[1] * r[1]) / rr
        lo, hi = (t0, t1) if t0 <= t1 else (t1, t0)
        lo = max(lo, 0.0)
        hi = min(hi, 1.0)
        if lo > hi + eps:
            return None
        start = (p[0] + lo * r[0], p[1] + lo * r[1])
        end = (p[0] + hi * r[0], p[1] + hi * r[1])
        if abs(lo - hi) < eps:
            return start
        return (start, end)

    if abs(rxs) < eps:
        # Parallel, non-collinear.
        return None

    t = _cross(qmp, s) / rxs
    u = qmpxr / rxs

    if -eps <= t <= 1 + eps and -eps <= u <= 1 + eps:
        return (p[0] + t * r[0], p[1] + t * r[1])

    return None