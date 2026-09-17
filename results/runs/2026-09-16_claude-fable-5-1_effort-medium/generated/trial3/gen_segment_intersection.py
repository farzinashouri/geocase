"""Exact intersection of two 2D line segments.

`segment_intersection(a, b)` returns:
  * ``None``                      -- the segments share no point,
  * ``(x, y)``                    -- they share exactly one point,
  * ``((xa, ya), (xb, yb))``      -- they overlap along a segment.

Arithmetic is done with ``fractions.Fraction`` so that collinearity and
touching-endpoint cases are decided exactly rather than by float tolerance.
Degenerate (zero-length) segments are treated as points.
"""

from fractions import Fraction
from typing import Optional, Tuple, Union

Point = Tuple[float, float]
Segment = Tuple[Point, Point]
Result = Union[None, Point, Segment]


def _frac_point(p) -> Tuple[Fraction, Fraction]:
    return Fraction(p[0]), Fraction(p[1])


def _cross(ax: Fraction, ay: Fraction, bx: Fraction, by: Fraction) -> Fraction:
    return ax * by - ay * bx


def _to_float_point(p: Tuple[Fraction, Fraction]) -> Point:
    return float(p[0]), float(p[1])


def _on_segment(p, s0, s1) -> bool:
    """True if point p lies on the closed segment s0-s1 (all Fractions)."""
    if _cross(s1[0] - s0[0], s1[1] - s0[1], p[0] - s0[0], p[1] - s0[1]) != 0:
        return False
    return (min(s0[0], s1[0]) <= p[0] <= max(s0[0], s1[0])
            and min(s0[1], s1[1]) <= p[1] <= max(s0[1], s1[1]))


def segment_intersection(a: Segment, b: Segment) -> Result:
    p0, p1 = _frac_point(a[0]), _frac_point(a[1])
    q0, q1 = _frac_point(b[0]), _frac_point(b[1])

    rx, ry = p1[0] - p0[0], p1[1] - p0[1]
    sx, sy = q1[0] - q0[0], q1[1] - q0[1]
    a_is_point = rx == 0 and ry == 0
    b_is_point = sx == 0 and sy == 0

    # Degenerate cases: one or both segments are single points.
    if a_is_point and b_is_point:
        return _to_float_point(p0) if p0 == q0 else None
    if a_is_point:
        return _to_float_point(p0) if _on_segment(p0, q0, q1) else None
    if b_is_point:
        return _to_float_point(q0) if _on_segment(q0, p0, p1) else None

    denom = _cross(rx, ry, sx, sy)
    wx, wy = q0[0] - p0[0], q0[1] - p0[1]

    if denom != 0:
        # Proper (non-parallel) lines: a single crossing point at most.
        t = _cross(wx, wy, sx, sy) / denom
        u = _cross(wx, wy, rx, ry) / denom
        if 0 <= t <= 1 and 0 <= u <= 1:
            return _to_float_point((p0[0] + t * rx, p0[1] + t * ry))
        return None

    # Parallel lines.
    if _cross(wx, wy, rx, ry) != 0:
        return None  # parallel but not collinear

    # Collinear: project b's endpoints onto a's parameter line.
    rr = rx * rx + ry * ry
    t0 = (wx * rx + wy * ry) / rr
    t1 = t0 + (sx * rx + sy * ry) / rr
    lo, hi = max(Fraction(0), min(t0, t1)), min(Fraction(1), max(t0, t1))

    if lo > hi:
        return None
    if lo == hi:
        return _to_float_point((p0[0] + lo * rx, p0[1] + lo * ry))
    start = (p0[0] + lo * rx, p0[1] + lo * ry)
    end = (p0[0] + hi * rx, p0[1] + hi * ry)
    return _to_float_point(start), _to_float_point(end)