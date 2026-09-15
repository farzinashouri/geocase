"""Exact-as-practical intersection of two planar line segments.

``segment_intersection(a, b)`` takes two segments written as
``((x1, y1), (x2, y2))`` and returns their shared geometry:

* ``None`` when the segments have no point in common,
* ``(x, y)`` when they meet in exactly one point,
* ``((xa, ya), (xb, yb))`` when they overlap along a stretch of a common line.

The module is pure standard library and has no import-time side effects.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence, Tuple, Union

__all__ = ["segment_intersection", "DEFAULT_REL_TOL"]

Point = Tuple[float, float]
Segment = Tuple[Point, Point]

#: Tolerance used for the degeneracy, parallelism and containment tests,
#: expressed relative to the largest coordinate magnitude of the inputs.
DEFAULT_REL_TOL = 1e-12


def segment_intersection(
    a: Sequence[Sequence[float]],
    b: Sequence[Sequence[float]],
    rel_tol: float = DEFAULT_REL_TOL,
) -> Optional[Union[Point, Segment]]:
    """Return the intersection of the 2D segments ``a`` and ``b``.

    Both segments are given as ``((x1, y1), (x2, y2))`` in a planar (already
    projected) coordinate system. The result is ``None`` for disjoint segments,
    a single ``(x, y)`` point when they touch or cross in one place, and a
    ``((xa, ya), (xb, yb))`` pair when they are collinear and share more than
    one point.

    Zero-length segments are accepted and treated as points.

    ``rel_tol`` scales the tolerance used to decide whether segments are
    degenerate, parallel, collinear, or just barely touching; the absolute
    tolerance is ``rel_tol`` times the largest coordinate magnitude involved,
    so the answer does not change when the whole configuration is rescaled.
    Pass ``rel_tol=0.0`` for strict floating-point comparisons.

    >>> segment_intersection(((0.0, 0.0), (2.0, 2.0)), ((0.0, 2.0), (2.0, 0.0)))
    (1.0, 1.0)
    >>> segment_intersection(((0.0, 0.0), (4.0, 0.0)), ((1.0, 0.0), (6.0, 0.0)))
    ((1.0, 0.0), (4.0, 0.0))
    >>> segment_intersection(((0.0, 0.0), (1.0, 0.0)), ((2.0, 0.0), (3.0, 0.0))) is None
    True
    """
    if not math.isfinite(rel_tol) or rel_tol < 0.0:
        raise ValueError(f"rel_tol must be a finite non-negative number, got {rel_tol!r}")

    p0, p1 = _as_segment(a, "a")
    q0, q1 = _as_segment(b, "b")

    # Absolute tolerance, in coordinate units, derived from the data's magnitude.
    eps = rel_tol * max(abs(c) for point in (p0, p1, q0, q1) for c in point)

    da = _sub(p1, p0)
    db = _sub(q1, q0)
    len_a = math.hypot(da[0], da[1])
    len_b = math.hypot(db[0], db[1])

    # Degenerate inputs: a segment shorter than the tolerance is just a point.
    if len_a <= eps and len_b <= eps:
        return p0 if math.dist(p0, q0) <= eps else None
    if len_a <= eps:
        return p0 if _point_on_segment(p0, q0, db, len_b, eps) else None
    if len_b <= eps:
        return q0 if _point_on_segment(q0, p0, da, len_a, eps) else None

    # ``denom`` is len_a * len_b * sin(angle); comparing it against
    # eps * max(len_a, len_b) asks whether the far end of the shorter segment
    # lies within eps of the other segment's supporting line.
    denom = _cross(da, db)
    if abs(denom) <= eps * max(len_a, len_b):
        return _parallel_intersection(p0, p1, da, len_a, q0, q1, eps)

    w = _sub(q0, p0)
    t = _cross(w, db) / denom  # position along a
    u = _cross(w, da) / denom  # position along b
    if not -eps / len_a <= t <= 1.0 + eps / len_a:
        return None
    if not -eps / len_b <= u <= 1.0 + eps / len_b:
        return None
    return _lerp(p0, p1, min(1.0, max(0.0, t)))


def _parallel_intersection(
    p0: Point,
    p1: Point,
    da: Point,
    len_a: float,
    q0: Point,
    q1: Point,
    eps: float,
) -> Optional[Union[Point, Segment]]:
    """Intersect two parallel segments, the first of which is non-degenerate."""
    if abs(_cross(_sub(q0, p0), da)) > eps * len_a:
        return None  # parallel, but on different lines

    # Parameterise everything along ``a``, with p0 at 0.0 and p1 at 1.0. The
    # overlap always starts and ends at one of the four original endpoints, so
    # carry those endpoints along and return them verbatim, free of round-off.
    inv = 1.0 / (len_a * len_a)
    tb0 = _dot(_sub(q0, p0), da) * inv
    tb1 = _dot(_sub(q1, p0), da) * inv
    if tb0 <= tb1:
        b_lo, b_hi = (tb0, q0), (tb1, q1)
    else:
        b_lo, b_hi = (tb1, q1), (tb0, q0)

    start = b_lo if b_lo[0] > 0.0 else (0.0, p0)
    end = b_hi if b_hi[0] < 1.0 else (1.0, p1)

    eps_t = eps / len_a
    if start[0] > end[0] + eps_t:
        return None
    if end[0] - start[0] <= eps_t:
        return start[1]
    return (start[1], end[1])


def _point_on_segment(
    point: Point, s0: Point, ds: Point, len_s: float, eps: float
) -> bool:
    """Is ``point`` within ``eps`` of the segment running from ``s0`` along ``ds``?"""
    w = _sub(point, s0)
    if abs(_cross(w, ds)) > eps * len_s:  # perpendicular distance
        return False
    t = _dot(w, ds) / (len_s * len_s)
    return -eps / len_s <= t <= 1.0 + eps / len_s


def _as_segment(value: Sequence[Sequence[float]], name: str) -> Segment:
    try:
        (x1, y1), (x2, y2) = value
        p0 = (float(x1), float(y1))
        p1 = (float(x2), float(y2))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"segment {name} must be ((x1, y1), (x2, y2)), got {value!r}"
        ) from exc
    if not all(math.isfinite(c) for c in p0 + p1):
        raise ValueError(f"segment {name} has non-finite coordinates: {value!r}")
    return p0, p1


def _sub(u: Point, v: Point) -> Point:
    return (u[0] - v[0], u[1] - v[1])


def _cross(u: Point, v: Point) -> float:
    return u[0] * v[1] - u[1] * v[0]


def _dot(u: Point, v: Point) -> float:
    return u[0] * v[0] + u[1] * v[1]


def _lerp(p0: Point, p1: Point, t: float) -> Point:
    """Interpolate p0 -> p1, exact at both ends and never outside them."""
    s = 1.0 - t
    return (s * p0[0] + t * p1[0], s * p0[1] + t * p1[1])