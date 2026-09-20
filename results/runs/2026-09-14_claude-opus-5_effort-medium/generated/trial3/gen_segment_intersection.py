"""Planar line-segment intersection.

Computes the set-theoretic intersection of two 2D line segments.  The
intersection of two segments is always empty, a single point, or a
sub-segment (when the two segments are collinear and overlap), so the
result is returned as ``None``, ``(x, y)`` or ``((xa, ya), (xb, yb))``.

Pure standard library; importing this module has no side effects.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence, Tuple, Union

__all__ = ["segment_intersection"]

Point = Tuple[float, float]
Segment = Tuple[Point, Point]
Result = Union[None, Point, Segment]

# Relative tolerance used for every comparison.  Coordinates are doubles, so
# ~1e-16 is the noise floor; 1e-12 leaves room for a few accumulated ulps in
# the cross/dot products while staying far below any meaningful geometry.
_REL_EPS = 1e-12


def _as_point(p: Sequence[float]) -> Point:
    x, y = p
    x = float(x)
    y = float(y)
    if not (math.isfinite(x) and math.isfinite(y)):
        raise ValueError("segment coordinates must be finite")
    return (x, y)


def _as_segment(s: Sequence[Sequence[float]]) -> Segment:
    p, q = s
    return (_as_point(p), _as_point(q))


def _sub(p: Point, q: Point) -> Point:
    return (p[0] - q[0], p[1] - q[1])


def _cross(u: Point, v: Point) -> float:
    return u[0] * v[1] - u[1] * v[0]


def _dot(u: Point, v: Point) -> float:
    return u[0] * v[0] + u[1] * v[1]


def _norm(u: Point) -> float:
    return math.hypot(u[0], u[1])


def _lerp(a: Point, d: Point, t: float) -> Point:
    """Point at parameter ``t`` along the segment starting at ``a`` with
    direction ``d``, returning the endpoints exactly at t == 0 and t == 1."""
    if t == 0.0:
        return a
    if t == 1.0:
        return (a[0] + d[0], a[1] + d[1])
    return (a[0] + t * d[0], a[1] + t * d[1])


def _scale_of(*points: Point) -> float:
    """Magnitude of the problem, used to turn relative into absolute tolerances."""
    m = 1.0
    for x, y in points:
        m = max(m, abs(x), abs(y))
    return m


def _point_on_segment(p: Point, a1: Point, a2: Point, eps_len: float) -> bool:
    d = _sub(a2, a1)
    w = _sub(p, a1)
    dd = _dot(d, d)
    if dd <= eps_len * eps_len:  # degenerate segment: a single point
        return _norm(w) <= eps_len
    # Distance from p to the infinite line through a1, a2.
    if abs(_cross(w, d)) > eps_len * math.sqrt(dd):
        return False
    t = _dot(w, d) / dd
    tp = eps_len / math.sqrt(dd)
    return -tp <= t <= 1.0 + tp


def segment_intersection(
    a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]
) -> Result:
    """Intersect two 2D segments ``((x1, y1), (x2, y2))``.

    Returns ``None`` when the segments share no point, ``(x, y)`` when they
    share exactly one, and ``((xa, ya), (xb, yb))`` when they share a
    sub-segment (collinear overlap).  Zero-length segments are accepted and
    treated as points.
    """
    a1, a2 = _as_segment(a)
    b1, b2 = _as_segment(b)

    scale = _scale_of(a1, a2, b1, b2)
    eps_len = _REL_EPS * scale

    d = _sub(a2, a1)  # direction of a
    e = _sub(b2, b1)  # direction of b
    len_d = _norm(d)
    len_e = _norm(e)

    a_is_point = len_d <= eps_len
    b_is_point = len_e <= eps_len

    # --- degenerate inputs -------------------------------------------------
    if a_is_point and b_is_point:
        return a1 if _norm(_sub(b1, a1)) <= eps_len else None
    if a_is_point:
        return a1 if _point_on_segment(a1, b1, b2, eps_len) else None
    if b_is_point:
        return b1 if _point_on_segment(b1, a1, a2, eps_len) else None

    # --- general position: the supporting lines cross in one point ---------
    denom = _cross(d, e)
    # |cross| is an area; compare it against the area scale of the two
    # directions, with an absolute floor so tiny-but-real segments still work.
    if abs(denom) > _REL_EPS * max(len_d * len_e, scale * scale):
        w = _sub(b1, a1)
        t = _cross(w, e) / denom  # parameter along a
        u = _cross(w, d) / denom  # parameter along b
        tp = eps_len / len_d
        up = eps_len / len_e
        if not (-tp <= t <= 1.0 + tp and -up <= u <= 1.0 + up):
            return None
        return _lerp(a1, d, min(1.0, max(0.0, t)))

    # --- parallel: intersect only if collinear and overlapping -------------
    w = _sub(b1, a1)
    if abs(_cross(w, d)) > eps_len * len_d:
        return None  # parallel but offset

    # Project b's endpoints onto a's parameter axis.
    dd = _dot(d, d)
    t0 = _dot(w, d) / dd
    t1 = _dot(_sub(b2, a1), d) / dd
    if t0 > t1:
        t0, t1 = t1, t0

    tp = eps_len / len_d
    lo = max(0.0, t0)
    hi = min(1.0, t1)
    if hi < lo - tp:
        return None
    if hi - lo <= tp:  # touching at (essentially) one point
        return _lerp(a1, d, min(1.0, max(0.0, 0.5 * (lo + hi))))

    return (_lerp(a1, d, lo), _lerp(a1, d, hi))