```python
"""Exact intersection of two 2D line segments.

segment_intersection(a, b) returns None, a point (x, y), or a segment
((xa, ya), (xb, yb)) describing the shared portion of the two segments.
Arithmetic is done with fractions.Fraction so collinear and touching cases
are decided exactly; results are converted back to floats.
"""

from fractions import Fraction
from typing import Optional, Tuple, Union

Point = Tuple[float, float]
Segment = Tuple[Point, Point]
Result = Union[None, Point, Segment]


def _frac(p) -> Tuple[Fraction, Fraction]:
    return Fraction(p[0]), Fraction(p[1])


def _cross(ax, ay, bx, by) -> Fraction:
    return ax * by - ay * bx


def _to_point(x: Fraction, y: Fraction) -> Point:
    return float(x), float(y)


def segment_intersection(a: Segment, b: Segment) -> Result:
    (p1x, p1y), (p2x, p2y) = _frac(a[0]), _frac(a[1])
    (q1x, q1y), (q2x, q2y) = _frac(b[0]), _frac(b[1])

    d1x, d1y = p2x - p1x, p2y - p1y
    d2x, d2y = q2x - q1x, q2y - q1y

    denom = _cross(d1x, d1y, d2x, d2y)

    if denom != 0:
        # Proper (non-parallel) segments: solve p1 + t*d1 == q1 + u*d2.
        wx, wy = q1x - p1x, q1y - p1y
        t = _cross(wx, wy, d2x, d2y) / denom
        u = _cross(wx, wy, d1x, d1y) / denom
        if 0 <= t <= 1 and 0 <= u <= 1:
            return _to_point(p1x + t * d1x, p1y + t * d1y)
        return None

    # Parallel, collinear, or degenerate (one or both segments are points).
    if d1x != 0 or d1y != 0:
        dx, dy = d1x, d1y
    elif d2x != 0 or d2y != 0:
        dx, dy = d2x, d2y
    else:
        # Both segments are single points.
        if p1x == q1x and p1y == q1y:
            return _to_point(p1x, p1y)
        return None

    # All four endpoints must lie on the line through p1 with direction d.
    for px, py in ((p2x, p2y), (q1x, q1y), (q2x, q2y)):
        if _cross(px - p1x, py - p1y, dx, dy) != 0:
            return None

    # Parametrise along d (scalar projection, scaled by |d|^2).
    def s(px, py) -> Fraction:
        return (px - p1x) * dx + (py - p1y) * dy

    a_lo, a_hi = sorted((s(p1x, p1y), s(p2x, p2y)))
    b_lo, b_hi = sorted((s(q1x, q1y), s(q2x, q2y)))

    lo = max(a_lo, b_lo)
    hi = min(a_hi, b_hi)
    if lo > hi:
        return None

    dd = dx * dx + dy * dy

    def at(sv: Fraction) -> Point:
        return _to_point(p1x + dx * sv / dd, p1y + dy * sv / dd)

    if lo == hi:
        return at(lo)
    return at(lo), at(hi)
```