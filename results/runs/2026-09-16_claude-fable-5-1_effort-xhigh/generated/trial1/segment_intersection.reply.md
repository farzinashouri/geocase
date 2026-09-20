Both the file write and the test run were declined, so the module below is untested in this session, though the logic uses exact rational arithmetic and was checked by hand against crossing, touching, collinear-overlap, parallel, and degenerate cases.

```python
"""Exact intersection of two planar 2D line segments.

All orientation, parallelism and parameter arithmetic is done with
:class:`fractions.Fraction`, so collinearity and containment tests are exact
for any finite float input.  Results are converted back to ``float``
(correctly rounded from the exact rational value).

Importing this module has no side effects.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Tuple, Union

__all__ = ["segment_intersection", "Point", "Segment"]

Point = Tuple[float, float]
Segment = Tuple[Point, Point]


def _frac(v) -> Fraction:
    """Convert a coordinate to an exact Fraction."""
    if isinstance(v, (int, Fraction)):
        return Fraction(v)
    return Fraction(float(v))  # exact for finite floats; raises on nan/inf


def _cross(ax: Fraction, ay: Fraction, bx: Fraction, by: Fraction) -> Fraction:
    return ax * by - ay * bx


def _dot(ax: Fraction, ay: Fraction, bx: Fraction, by: Fraction) -> Fraction:
    return ax * bx + ay * by


def _point(x: Fraction, y: Fraction) -> Point:
    return (float(x), float(y))


def _point_on_segment(
    px: Fraction, py: Fraction,
    sx: Fraction, sy: Fraction,
    dx: Fraction, dy: Fraction,
) -> bool:
    """True if point P lies on the non-degenerate segment S + t*D, 0 <= t <= 1."""
    wx, wy = px - sx, py - sy
    if _cross(wx, wy, dx, dy) != 0:
        return False
    proj = _dot(wx, wy, dx, dy)
    return 0 <= proj <= _dot(dx, dy, dx, dy)


def segment_intersection(a, b) -> Union[None, Point, Segment]:
    """Intersect two 2D line segments.

    Each segment is ``((x1, y1), (x2, y2))`` with numeric coordinates.

    Returns:
      * ``None`` if the segments share no point;
      * a point ``(x, y)`` if they share exactly one point (a proper
        crossing, a touch at an endpoint, or a single-point collinear
        contact);
      * a segment ``((xa, ya), (xb, yb))`` if they share more than one point
        (a collinear overlap of positive length).  The endpoints are ordered
        in the direction of segment ``a``.

    Zero-length segments are treated as points.
    """
    (p1, p2), (q1, q2) = a, b
    p1x, p1y = _frac(p1[0]), _frac(p1[1])
    p2x, p2y = _frac(p2[0]), _frac(p2[1])
    q1x, q1y = _frac(q1[0]), _frac(q1[1])
    q2x, q2y = _frac(q2[0]), _frac(q2[1])

    rx, ry = p2x - p1x, p2y - p1y  # direction of a
    sx, sy = q2x - q1x, q2y - q1y  # direction of b
    a_degenerate = rx == 0 and ry == 0
    b_degenerate = sx == 0 and sy == 0

    # --- Degenerate (point) segments ---------------------------------------
    if a_degenerate and b_degenerate:
        return _point(p1x, p1y) if (p1x, p1y) == (q1x, q1y) else None
    if a_degenerate:
        on_b = _point_on_segment(p1x, p1y, q1x, q1y, sx, sy)
        return _point(p1x, p1y) if on_b else None
    if b_degenerate:
        on_a = _point_on_segment(q1x, q1y, p1x, p1y, rx, ry)
        return _point(q1x, q1y) if on_a else None

    qpx, qpy = q1x - p1x, q1y - p1y
    denom = _cross(rx, ry, sx, sy)

    # --- Non-parallel: at most one common point ----------------------------
    if denom != 0:
        t = _cross(qpx, qpy, sx, sy) / denom  # parameter along a
        u = _cross(qpx, qpy, rx, ry) / denom  # parameter along b
        if 0 <= t <= 1 and 0 <= u <= 1:
            return _point(p1x + t * rx, p1y + t * ry)
        return None

    # --- Parallel ------------------------------------------------------------
    if _cross(qpx, qpy, rx, ry) != 0:
        return None  # parallel but not collinear

    # Collinear: project b's endpoints onto a's parameter line.
    rr = _dot(rx, ry, rx, ry)
    t0 = _dot(qpx, qpy, rx, ry) / rr
    t1 = t0 + _dot(sx, sy, rx, ry) / rr
    lo = max(Fraction(0), min(t0, t1))
    hi = min(Fraction(1), max(t0, t1))

    if lo > hi:
        return None
    if lo == hi:
        return _point(p1x + lo * rx, p1y + lo * ry)
    return (
        _point(p1x + lo * rx, p1y + lo * ry),
        _point(p1x + hi * rx, p1y + hi * ry),
    )
```