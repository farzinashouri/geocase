"""Exact 2D segment intersection.

Uses fractions for exact arithmetic so that collinear/degenerate cases are
classified correctly; results are returned as floats.
"""

from fractions import Fraction
from typing import Optional, Tuple, Union

Point = Tuple[float, float]
Segment = Tuple[Point, Point]
Result = Union[None, Point, Segment]


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _on_segment(p, a, b):
    """True if collinear point p lies within the bounding box of segment ab."""
    return (min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
            and min(a[1], b[1]) <= p[1] <= max(a[1], b[1]))


def _to_frac(p):
    return (Fraction(p[0]), Fraction(p[1]))


def _to_float(p) -> Point:
    return (float(p[0]), float(p[1]))


def segment_intersection(a: Segment, b: Segment) -> Result:
    """Intersect two 2D line segments.

    Returns None if disjoint, a point (x, y) if they share exactly one point,
    or a segment ((xa, ya), (xb, yb)) if they overlap along a positive length.
    """
    p1, p2 = _to_frac(a[0]), _to_frac(a[1])
    q1, q2 = _to_frac(b[0]), _to_frac(b[1])

    d1 = _cross(q1, q2, p1)
    d2 = _cross(q1, q2, p2)
    d3 = _cross(p1, p2, q1)
    d4 = _cross(p1, p2, q2)

    # Proper crossing: each segment straddles the other's line.
    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
       ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        t = d1 / (d1 - d2)
        return _to_float((p1[0] + t * (p2[0] - p1[0]),
                          p1[1] + t * (p2[1] - p1[1])))

    if d1 == 0 and d2 == 0 and d3 == 0 and d4 == 0:
        # Collinear (or one/both segments degenerate). Project onto the
        # dominant axis of the non-degenerate segment and intersect intervals.
        if p1 != p2:
            base, dirv = p1, (p2[0] - p1[0], p2[1] - p1[1])
        elif q1 != q2:
            base, dirv = q1, (q2[0] - q1[0], q2[1] - q1[1])
        else:
            return _to_float(p1) if p1 == q1 else None

        def param(pt):
            return ((pt[0] - base[0]) * dirv[0] + (pt[1] - base[1]) * dirv[1])

        lo_a, hi_a = sorted((param(p1), param(p2)))
        lo_b, hi_b = sorted((param(q1), param(q2)))
        lo, hi = max(lo_a, lo_b), min(hi_a, hi_b)
        if lo > hi:
            return None

        def point_at(s):
            k = s / (dirv[0] ** 2 + dirv[1] ** 2)
            return (base[0] + k * dirv[0], base[1] + k * dirv[1])

        if lo == hi:
            return _to_float(point_at(lo))
        return (_to_float(point_at(lo)), _to_float(point_at(hi)))

    # Touching cases: an endpoint of one lies on the other segment.
    if d1 == 0 and _on_segment(p1, q1, q2):
        return _to_float(p1)
    if d2 == 0 and _on_segment(p2, q1, q2):
        return _to_float(p2)
    if d3 == 0 and _on_segment(q1, p1, p2):
        return _to_float(q1)
    if d4 == 0 and _on_segment(q2, p1, p2):
        return _to_float(q2)

    return None