"""Exact intersection of two planar line segments.

``segment_intersection`` treats both inputs as *closed* segments and reports the
shape of the set of points they share:

* ``None``                   -- the segments are disjoint;
* ``(x, y)``                 -- they meet in exactly one point;
* ``((xa, ya), (xb, yb))``   -- they overlap along a sub-segment.

All predicates are evaluated in exact rational arithmetic
(:class:`fractions.Fraction` round-trips a binary float losslessly), so the
classification returned is the true answer for the coordinates *as given*: there
is no epsilon and no near-parallel guesswork.  Two segments that are merely
*almost* collinear genuinely cross in a single point, and that is what is
reported.  Only the final conversion back to ``float`` rounds, and any endpoint
carried over from the input survives it unchanged.

Degenerate (zero-length) segments are accepted and behave as the single point
they describe.
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Any, Optional, Tuple, Union

__all__ = ["segment_intersection"]

Point = Tuple[float, float]
Segment = Tuple[Point, Point]
Result = Optional[Union[Point, Segment]]

_Exact = Tuple[Fraction, Fraction]

_ZERO = Fraction(0)
_ONE = Fraction(1)


def segment_intersection(a: Segment, b: Segment) -> Result:
    """Intersect two closed 2D segments.

    Parameters
    ----------
    a, b:
        Segments as ``((x1, y1), (x2, y2))`` with finite planar coordinates.
        The two endpoints may coincide, in which case the segment is a point.

    Returns
    -------
    ``None`` when the segments share no point, ``(x, y)`` when they share
    exactly one, and ``((xa, ya), (xb, yb))`` when they share more than one.
    An overlap is oriented along ``a``: from the end nearer ``a[0]`` towards
    the end nearer ``a[1]``.

    Raises
    ------
    TypeError
        If an argument is not a pair of coordinate pairs.
    ValueError
        If a coordinate is NaN or infinite.
    """
    p1, p2 = _exact_segment(a, "a")
    q1, q2 = _exact_segment(b, "b")

    # Degenerate inputs reduce to a point-membership test.
    if p1 == p2:
        if q1 == q2:
            return _point(p1) if p1 == q1 else None
        return _point(p1) if _on_segment(p1, q1, q2) else None
    if q1 == q2:
        return _point(q1) if _on_segment(q1, p1, p2) else None

    rx, ry = p2[0] - p1[0], p2[1] - p1[1]      # direction of a
    sx, sy = q2[0] - q1[0], q2[1] - q1[1]      # direction of b
    wx, wy = q1[0] - p1[0], q1[1] - p1[1]      # start of b relative to start of a

    denom = rx * sy - ry * sx
    if denom != _ZERO:
        # Non-parallel: the supporting lines meet once, at p1 + t*r == q1 + u*s.
        t = (wx * sy - wy * sx) / denom
        if not _ZERO <= t <= _ONE:
            return None
        u = (wx * ry - wy * rx) / denom
        if not _ZERO <= u <= _ONE:
            return None
        return _point((p1[0] + t * rx, p1[1] + t * ry))

    # Parallel: unless b starts on a's supporting line, the two never meet.
    if wx * ry - wy * rx != _ZERO:
        return None

    # Collinear: intersect the segments as intervals in a's parameter space,
    # where a itself spans [0, 1].
    squared_length = rx * rx + ry * ry
    t0 = (wx * rx + wy * ry) / squared_length
    t1 = t0 + (sx * rx + sy * ry) / squared_length
    if t1 < t0:
        t0, t1 = t1, t0

    lo = t0 if t0 > _ZERO else _ZERO
    hi = t1 if t1 < _ONE else _ONE
    if lo > hi:
        return None
    if lo == hi:
        return _point((p1[0] + lo * rx, p1[1] + lo * ry))
    return (
        _point((p1[0] + lo * rx, p1[1] + lo * ry)),
        _point((p1[0] + hi * rx, p1[1] + hi * ry)),
    )


def _on_segment(point: _Exact, s1: _Exact, s2: _Exact) -> bool:
    """Whether ``point`` lies on the closed segment ``s1``--``s2``."""
    px, py = point
    x1, y1 = s1
    x2, y2 = s2
    if (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1) != _ZERO:
        return False
    return min(x1, x2) <= px <= max(x1, x2) and min(y1, y2) <= py <= max(y1, y2)


def _exact_segment(segment: Any, name: str) -> Tuple[_Exact, _Exact]:
    try:
        start, end = segment
    except (TypeError, ValueError):
        raise TypeError(
            f"segment {name} must be a pair of endpoints, got {segment!r}"
        ) from None
    return _exact_point(start, name), _exact_point(end, name)


def _exact_point(point: Any, name: str) -> _Exact:
    try:
        x, y = point
    except (TypeError, ValueError):
        raise TypeError(
            f"endpoints of segment {name} must be (x, y) pairs, got {point!r}"
        ) from None
    return _exact(x, name), _exact(y, name)


def _exact(coordinate: Any, name: str) -> Fraction:
    """Convert a coordinate to an exact rational, losslessly for floats."""
    if isinstance(coordinate, (int, Fraction)):
        return Fraction(coordinate)
    value = float(coordinate)
    if not math.isfinite(value):
        raise ValueError(f"segment {name} has a non-finite coordinate: {coordinate!r}")
    return Fraction(value)


def _point(point: _Exact) -> Point:
    return (float(point[0]), float(point[1]))