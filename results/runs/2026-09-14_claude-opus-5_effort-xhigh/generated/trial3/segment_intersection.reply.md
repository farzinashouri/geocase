```python
"""Exact intersection of two planar line segments.

Two straight segments in the plane have in common either nothing, exactly
one point, or -- when they are collinear and overlap -- a whole
sub-segment.  :func:`segment_intersection` reports each of those three
outcomes directly, as ``None``, a point, or a segment.

Every predicate (parallel? collinear? inside the parameter range?) and the
intersection point itself are evaluated in exact rational arithmetic
(:class:`fractions.Fraction`, which is lossless for binary floats).  There
is therefore no epsilon to tune and no catastrophic cancellation near
grazing or nearly-parallel configurations: the result is the
mathematically exact intersection of the segments *as given*, rounded to
float only on the way out.  The flip side is that a near miss is a miss --
endpoints differing in the last bit do not touch.  Snap or round the
coordinates beforehand if tolerant behaviour is wanted.

>>> segment_intersection(((0.0, 0.0), (2.0, 2.0)), ((0.0, 2.0), (2.0, 0.0)))
(1.0, 1.0)
>>> segment_intersection(((0.0, 0.0), (1.0, 0.0)), ((0.0, 1.0), (1.0, 1.0)))
>>> segment_intersection(((0.0, 0.0), (2.0, 0.0)), ((1.0, 0.0), (3.0, 0.0)))
((1.0, 0.0), (2.0, 0.0))
>>> segment_intersection(((0.0, 0.0), (1.0, 1.0)), ((1.0, 1.0), (2.0, 0.0)))
(1.0, 1.0)
"""

from __future__ import annotations

from fractions import Fraction
from math import isfinite
from typing import Optional, Tuple, Union

__all__ = ["segment_intersection"]

Point = Tuple[float, float]
Segment = Tuple[Point, Point]
Result = Union[None, Point, Segment]

_Exact = Tuple[Fraction, Fraction]

_ZERO = Fraction(0)
_ONE = Fraction(1)
_ORIGIN: _Exact = (_ZERO, _ZERO)


def segment_intersection(a: Segment, b: Segment) -> Result:
    """Return what segments ``a`` and ``b`` have in common.

    Each argument is a 2D segment ``((x1, y1), (x2, y2))`` in a planar
    coordinate system.  A segment is closed: its endpoints belong to it.
    Degenerate (zero-length) segments are accepted and treated as the
    single point they describe.

    Returns
    -------
    None
        The segments share no point.
    (x, y)
        The segments share exactly one point.
    ((xa, ya), (xb, yb))
        The segments are collinear and overlap in more than one point;
        the two endpoints of the shared portion are returned ordered
        along the direction of ``a``.

    Raises
    ------
    TypeError
        If an argument is not a pair of coordinate pairs.
    ValueError
        If a coordinate is NaN or infinite.
    """
    p1, p2 = _as_segment(a, "a")
    q1, q2 = _as_segment(b, "b")

    # Cheap and exact rejection: disjoint bounding boxes share nothing.
    if (
        max(p1[0], p2[0]) < min(q1[0], q2[0])
        or max(q1[0], q2[0]) < min(p1[0], p2[0])
        or max(p1[1], p2[1]) < min(q1[1], q2[1])
        or max(q1[1], q2[1]) < min(p1[1], p2[1])
    ):
        return None

    r = (p2[0] - p1[0], p2[1] - p1[1])
    s = (q2[0] - q1[0], q2[1] - q1[1])

    # Degenerate segments: one or both collapse to a point.
    if r == _ORIGIN:
        if s == _ORIGIN:
            return _point(p1) if p1 == q1 else None
        return _point(p1) if _covers(q1, s, p1) else None
    if s == _ORIGIN:
        return _point(q1) if _covers(p1, r, q1) else None

    qp = (q1[0] - p1[0], q1[1] - p1[1])
    denom = _cross(r, s)

    if denom != _ZERO:
        # Non-parallel: the supporting lines meet in one point, which
        # counts only if it lies within both parameter ranges.
        t = _cross(qp, s) / denom
        u = _cross(qp, r) / denom
        if _ZERO <= t <= _ONE and _ZERO <= u <= _ONE:
            return _point(_along(p1, r, t))
        return None

    if _cross(qp, r) != _ZERO:
        return None  # Parallel but on distinct lines.

    # Collinear: clip b's parameter range against a's [0, 1].
    rr = _dot(r, r)
    t0 = _dot(qp, r) / rr
    t1 = t0 + _dot(s, r) / rr
    lo = max(min(t0, t1), _ZERO)
    hi = min(max(t0, t1), _ONE)

    if lo > hi:
        return None
    if lo == hi:
        return _point(_along(p1, r, lo))
    return _point(_along(p1, r, lo)), _point(_along(p1, r, hi))


def _cross(u: _Exact, v: _Exact) -> Fraction:
    return u[0] * v[1] - u[1] * v[0]


def _dot(u: _Exact, v: _Exact) -> Fraction:
    return u[0] * v[0] + u[1] * v[1]


def _along(base: _Exact, direction: _Exact, t: Fraction) -> _Exact:
    """The point ``base + t * direction``, exactly."""
    return (base[0] + t * direction[0], base[1] + t * direction[1])


def _covers(base: _Exact, direction: _Exact, pt: _Exact) -> bool:
    """Whether ``pt`` lies on the segment ``base -> base + direction``.

    ``direction`` must be non-zero.
    """
    offset = (pt[0] - base[0], pt[1] - base[1])
    if _cross(direction, offset) != _ZERO:
        return False
    projection = _dot(offset, direction)
    return _ZERO <= projection <= _dot(direction, direction)


def _point(pt: _Exact) -> Point:
    return (float(pt[0]), float(pt[1]))


def _as_segment(value: Segment, name: str) -> Tuple[_Exact, _Exact]:
    try:
        first, second = value
    except (TypeError, ValueError):
        raise TypeError(
            f"segment {name!r} must be a pair of points "
            f"((x1, y1), (x2, y2)), got {value!r}"
        ) from None
    return _as_point(first, name, 0), _as_point(second, name, 1)


def _as_point(value: Point, name: str, index: int) -> _Exact:
    try:
        x, y = value
    except (TypeError, ValueError):
        raise TypeError(
            f"endpoint {index} of segment {name!r} must be a pair "
            f"(x, y), got {value!r}"
        ) from None
    return _as_coord(x, name, index, "x"), _as_coord(y, name, index, "y")


def _as_coord(value: float, name: str, index: int, axis: str) -> Fraction:
    where = f"{axis} of endpoint {index} of segment {name!r}"
    try:
        coord = float(value)
    except (TypeError, ValueError):
        raise TypeError(f"{where} must be a real number, got {value!r}") from None
    if not isfinite(coord):
        raise ValueError(f"{where} must be finite, got {value!r}")
    return Fraction(coord)  # Exact: every finite float is a rational.
```