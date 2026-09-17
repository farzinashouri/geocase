"""Exact 2D line-segment intersection using rational arithmetic.

segment_intersection(a, b) returns:
    None                         -> the segments share no point
    (x, y)                       -> exactly one common point
    ((xa, ya), (xb, yb))         -> the shared portion (more than one point)

Coordinates are floats. All predicates and the final coordinates are
computed with exact fractions to avoid floating-point misclassification
of collinear / touching cases, then converted back to floats.
"""

from fractions import Fraction
from typing import Optional, Tuple, Union

Point = Tuple[float, float]
Segment = Tuple[Point, Point]
Result = Union[None, Point, Segment]


def _frac_point(p) -> Tuple[Fraction, Fraction]:
    return Fraction(p[0]), Fraction(p[1])


def _cross(ox, oy, ax, ay, bx, by) -> Fraction:
    """Cross product of (a - o) x (b - o)."""
    return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox)


def _to_float(p: Tuple[Fraction, Fraction]) -> Point:
    return float(p[0]), float(p[1])


def segment_intersection(a: Segment, b: Segment) -> Result:
    (p1x, p1y), (p2x, p2y) = _frac_point(a[0]), _frac_point(a[1])
    (q1x, q1y), (q2x, q2y) = _frac_point(b[0]), _frac_point(b[1])

    rx, ry = p2x - p1x, p2y - p1y  # direction of a
    sx, sy = q2x - q1x, q2y - q1y  # direction of b
    denom = rx * sy - ry * sx      # r x s

    if denom != 0:
        # Proper (non-parallel) lines: solve p1 + t*r = q1 + u*s.
        qpx, qpy = q1x - p1x, q1y - p1y
        t = (qpx * sy - qpy * sx) / denom
        u = (qpx * ry - qpy * rx) / denom
        if 0 <= t <= 1 and 0 <= u <= 1:
            return _to_float((p1x + t * rx, p1y + t * ry))
        return None

    # Parallel. Check collinearity: q1 must lie on line a.
    if _cross(p1x, p1y, p2x, p2y, q1x, q1y) != 0:
        return None

    # Collinear: project all points onto a parameter along a common axis.
    # Handle the degenerate cases where one or both segments are points.
    a_is_point = rx == 0 and ry == 0
    b_is_point = sx == 0 and sy == 0

    if a_is_point and b_is_point:
        return _to_float((p1x, p1y)) if (p1x, p1y) == (q1x, q1y) else None

    # Choose the non-degenerate direction as the projection axis.
    if a_is_point:
        dx, dy, ox, oy = sx, sy, q1x, q1y
    else:
        dx, dy, ox, oy = rx, ry, p1x, p1y
    dd = dx * dx + dy * dy

    def param(x, y) -> Fraction:
        return ((x - ox) * dx + (y - oy) * dy) / dd

    ta0, ta1 = sorted((param(p1x, p1y), param(p2x, p2y)))
    tb0, tb1 = sorted((param(q1x, q1y), param(q2x, q2y)))

    lo = max(ta0, tb0)
    hi = min(ta1, tb1)
    if lo > hi:
        return None

    def point_at(t: Fraction) -> Tuple[Fraction, Fraction]:
        return ox + t * dx, oy + t * dy

    if lo == hi:
        return _to_float(point_at(lo))
    return _to_float(point_at(lo)), _to_float(point_at(hi))