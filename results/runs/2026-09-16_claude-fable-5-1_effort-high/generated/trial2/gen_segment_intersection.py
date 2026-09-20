"""Exact-ish 2D segment intersection.

segment_intersection(a, b) returns:
  * None                       -- the segments share no point
  * (x, y)                     -- the segments share exactly one point
  * ((xa, ya), (xb, yb))       -- the segments overlap along a sub-segment

Segments are given as ((x1, y1), (x2, y2)). Degenerate segments (both
endpoints equal) are treated as points. Comparisons use a small tolerance
scaled to the magnitude of the input coordinates so that floating-point
round-off does not spuriously separate touching segments.
"""

from __future__ import annotations

from typing import Optional, Tuple, Union

Point = Tuple[float, float]
Segment = Tuple[Point, Point]

_REL_TOL = 1e-9


def _sub(p: Point, q: Point) -> Point:
    return (p[0] - q[0], p[1] - q[1])


def _cross(u: Point, v: Point) -> float:
    return u[0] * v[1] - u[1] * v[0]


def _dot(u: Point, v: Point) -> float:
    return u[0] * v[0] + u[1] * v[1]


def _norm(u: Point) -> float:
    return (u[0] * u[0] + u[1] * u[1]) ** 0.5


def _as_point(p) -> Point:
    return (float(p[0]), float(p[1]))


def _point_on_segment(p: Point, s1: Point, s2: Point, tol: float) -> bool:
    """True if p lies on segment s1-s2 within distance tol."""
    d = _sub(s2, s1)
    length = _norm(d)
    if length <= tol:
        return _norm(_sub(p, s1)) <= tol
    w = _sub(p, s1)
    # Perpendicular distance from the supporting line.
    if abs(_cross(w, d)) / length > tol:
        return False
    # Projection parameter along the segment, with tolerance in length units.
    t = _dot(w, d) / (length * length)
    tol_t = tol / length
    return -tol_t <= t <= 1.0 + tol_t


def segment_intersection(
    a: Segment, b: Segment
) -> Union[None, Point, Segment]:
    (pa1, pa2), (pb1, pb2) = a, b
    p1, p2 = _as_point(pa1), _as_point(pa2)
    q1, q2 = _as_point(pb1), _as_point(pb2)

    scale = max(
        1.0,
        abs(p1[0]), abs(p1[1]), abs(p2[0]), abs(p2[1]),
        abs(q1[0]), abs(q1[1]), abs(q2[0]), abs(q2[1]),
    )
    tol = _REL_TOL * scale  # tolerance in coordinate/length units

    r = _sub(p2, p1)
    s = _sub(q2, q1)
    len_r = _norm(r)
    len_s = _norm(s)

    # --- Degenerate cases: one or both segments are points -----------------
    if len_r <= tol and len_s <= tol:
        return p1 if _norm(_sub(p1, q1)) <= tol else None
    if len_r <= tol:
        return p1 if _point_on_segment(p1, q1, q2, tol) else None
    if len_s <= tol:
        return q1 if _point_on_segment(q1, p1, p2, tol) else None

    # --- General case -------------------------------------------------------
    qp = _sub(q1, p1)
    rxs = _cross(r, s)
    qpxr = _cross(qp, r)

    # Parallel test: |r x s| = |r||s| sin(theta); treat as parallel when the
    # perpendicular offset implied by the angle is below tolerance.
    if abs(rxs) <= tol * max(len_r, len_s):
        # Collinear test: distance of q1 from line through a.
        if abs(qpxr) / len_r > tol:
            return None  # parallel, distinct lines

        # Project b's endpoints onto a's parameter space.
        rr = len_r * len_r
        t_q1 = _dot(qp, r) / rr
        t_q2 = t_q1 + _dot(s, r) / rr
        tol_t = tol / len_r

        # Candidate endpoints with their parameter along a.
        candidates = [(0.0, p1), (1.0, p2), (t_q1, q1), (t_q2, q2)]
        lo_b, hi_b = (t_q1, t_q2) if t_q1 <= t_q2 else (t_q2, t_q1)
        t_start = max(0.0, lo_b)
        t_end = min(1.0, hi_b)

        if t_start > t_end + tol_t:
            return None  # collinear but disjoint
        if t_end - t_start <= tol_t:
            # Touch at a single point; prefer an original endpoint.
            t_mid = 0.5 * (t_start + t_end)
            best = min(candidates, key=lambda c: abs(c[0] - t_mid))
            return best[1]

        def _snap(t: float) -> Point:
            for tc, pc in candidates:
                if abs(tc - t) <= tol_t:
                    return pc
            return (p1[0] + t * r[0], p1[1] + t * r[1])

        return (_snap(t_start), _snap(t_end))

    # Non-parallel: solve p1 + t r = q1 + u s.
    t = _cross(qp, s) / rxs
    u = qpxr / rxs
    tol_t = tol / len_r
    tol_u = tol / len_s
    if not (-tol_t <= t <= 1.0 + tol_t and -tol_u <= u <= 1.0 + tol_u):
        return None

    # Snap to an original endpoint when the hit is within tolerance of one.
    if abs(t) <= tol_t:
        return p1
    if abs(t - 1.0) <= tol_t:
        return p2
    if abs(u) <= tol_u:
        return q1
    if abs(u - 1.0) <= tol_u:
        return q2

    t = min(1.0, max(0.0, t))
    return (p1[0] + t * r[0], p1[1] + t * r[1])


__all__ = ["segment_intersection"]