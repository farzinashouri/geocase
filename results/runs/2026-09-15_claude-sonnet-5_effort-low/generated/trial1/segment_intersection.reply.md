```python
"""Segment-segment intersection in 2D."""

from __future__ import annotations

Point = tuple[float, float]
Segment = tuple[Point, Point]

_EPS = 1e-9


def _sub(p, q):
    return (p[0] - q[0], p[1] - q[1])


def _cross(u, v):
    return u[0] * v[1] - u[1] * v[0]


def _dot(u, v):
    return u[0] * v[0] + u[1] * v[1]


def _on_segment_collinear(p, a, b):
    # p assumed collinear with a,b; check within bounding box
    return (min(a[0], b[0]) - _EPS <= p[0] <= max(a[0], b[0]) + _EPS and
            min(a[1], b[1]) - _EPS <= p[1] <= max(a[1], b[1]) + _EPS)


def segment_intersection(a: Segment, b: Segment):
    p, p2 = a
    q, q2 = b
    r = _sub(p2, p)
    s = _sub(q2, q)
    rxs = _cross(r, s)
    qp = _sub(q, p)
    qpxr = _cross(qp, r)

    if abs(rxs) < _EPS:
        if abs(qpxr) > _EPS:
            return None
        # collinear
        r_len2 = _dot(r, r)
        if r_len2 < _EPS:
            # a is a point
            if _on_segment_collinear(p, q, q2):
                return p
            return None
        t0 = _dot(qp, r) / r_len2
        t1 = t0 + _dot(s, r) / r_len2
        tmin, tmax = min(t0, t1), max(t0, t1)
        lo = max(0.0, tmin)
        hi = min(1.0, tmax)
        if lo > hi + _EPS:
            return None
        pt_lo = (p[0] + lo * r[0], p[1] + lo * r[1])
        pt_hi = (p[0] + hi * r[0], p[1] + hi * r[1])
        if abs(lo - hi) < _EPS:
            return pt_lo
        return (pt_lo, pt_hi)

    t = _cross(qp, s) / rxs
    u = _cross(qp, r) / rxs
    if -_EPS <= t <= 1 + _EPS and -_EPS <= u <= 1 + _EPS:
        ix = p[0] + t * r[0]
        iy = p[1] + t * r[1]
        return (ix, iy)
    return None
```