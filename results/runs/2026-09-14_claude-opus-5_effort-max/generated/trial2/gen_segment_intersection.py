"""Exact intersection of two 2D line segments in a planar coordinate system.

The single public entry point is :func:`segment_intersection`, which classifies
the intersection of two segments as empty, a single point, or a shared
sub-segment.

Robustness
----------
Every decision -- are the segments collinear, does an endpoint lie on the other
segment, do they properly cross -- is made with exact arithmetic, so the result
is the mathematically correct one for the exact ``float`` values passed in.  The
orientation test uses a floating-point filter (Shewchuk's error bound) and falls
back to rational arithmetic only for the near-degenerate cases the filter cannot
certify, so the common case stays fast.

There is deliberately no tolerance parameter: "nearly collinear" and "collinear"
are different questions, and a tolerance that suits one coordinate system suits
no other.  Callers who want snapping should round coordinates onto the desired
grid before calling.
"""

from fractions import Fraction
from math import isfinite
from typing import Optional, Tuple, Union

__all__ = ["segment_intersection"]

Point = Tuple[float, float]
Segment = Tuple[Point, Point]

# Shewchuk's error bound for a 2x2 determinant in IEEE-754 double precision.
_EPS = 2.0 ** -53
_ORIENT_ERRBOUND = (3.0 + 16.0 * _EPS) * _EPS


def segment_intersection(a: Segment, b: Segment) -> Optional[Union[Point, Segment]]:
    """Intersect the 2D line segments ``a`` and ``b``.

    Each segment is given as ``((x1, y1), (x2, y2))``.  Zero-length segments
    (a single point) are accepted.

    Returns
    -------
    ``None``
        if the segments have no point in common;
    ``(x, y)``
        if they have exactly one point in common;
    ``((xa, ya), (xb, yb))``
        the endpoints of the shared portion if they have more than one point in
        common (the segments are collinear and overlap).  The endpoints are
        ordered lexicographically, which for collinear points is an ordering
        along the shared line.

    The two non-empty cases are told apart by the type of the first element: a
    ``float`` for a point, a ``tuple`` for a segment.

    Raises
    ------
    TypeError
        if an argument is not a pair of ``(x, y)`` pairs.
    ValueError
        if a coordinate is NaN or infinite.

    Examples
    --------
    >>> segment_intersection(((0.0, 0.0), (2.0, 2.0)), ((0.0, 2.0), (2.0, 0.0)))
    (1.0, 1.0)
    >>> segment_intersection(((0.0, 0.0), (1.0, 1.0)), ((1.0, 1.0), (2.0, 0.0)))
    (1.0, 1.0)
    >>> segment_intersection(((0.0, 0.0), (3.0, 0.0)), ((1.0, 0.0), (5.0, 0.0)))
    ((1.0, 0.0), (3.0, 0.0))
    >>> segment_intersection(((0.0, 0.0), (1.0, 0.0)), ((2.0, 0.0), (3.0, 0.0)))
    """
    a1, a2 = _as_segment(a, "a")
    b1, b2 = _as_segment(b, "b")

    # Degenerate (zero-length) segments: the machinery below assumes both
    # segments span a well-defined direction, so deal with them first.
    if a1 == a2 or b1 == b2:
        if a1 == a2 and b1 == b2:
            return a1 if a1 == b1 else None
        if a1 == a2:
            return a1 if _point_on_segment(a1, b1, b2) else None
        return b1 if _point_on_segment(b1, a1, a2) else None

    # Cheap exact rejection: no arithmetic, just comparisons of the inputs.
    if _bboxes_disjoint(a1, a2, b1, b2):
        return None

    # Which side of each supporting line the other segment's endpoints fall on.
    d1 = _orient(a1, a2, b1)
    d2 = _orient(a1, a2, b2)
    if d1 * d2 > 0:  # b lies strictly on one side of the line through a
        return None
    d3 = _orient(b1, b2, a1)
    d4 = _orient(b1, b2, a2)
    if d3 * d4 > 0:
        return None

    if d1 == 0 and d2 == 0:
        return _collinear_overlap(a1, a2, b1, b2)

    # Not collinear, so the segments share at most one point.  If it exists it
    # is either an endpoint lying on the other segment, or a proper crossing.
    if d1 == 0 and _in_bbox(b1, a1, a2):
        return b1
    if d2 == 0 and _in_bbox(b2, a1, a2):
        return b2
    if d3 == 0 and _in_bbox(a1, b1, b2):
        return a1
    if d4 == 0 and _in_bbox(a2, b1, b2):
        return a2
    if d1 * d2 < 0 and d3 * d4 < 0:
        return _crossing_point(a1, a2, b1, b2)
    return None


def _as_segment(seg, name: str) -> Segment:
    """Validate ``seg`` and coerce its coordinates to plain floats."""
    try:
        (x1, y1), (x2, y2) = seg
        p = (float(x1), float(y1))
        q = (float(x2), float(y2))
    except (TypeError, ValueError) as exc:
        raise TypeError(
            "{} must be a pair of (x, y) points, got {!r}".format(name, seg)
        ) from exc
    if not all(isfinite(c) for c in p + q):
        raise ValueError("{} has a non-finite coordinate: {!r}".format(name, seg))
    return p, q


def _orient(p: Point, q: Point, r: Point) -> int:
    """Sign of the cross product ``(q - p) x (r - p)``.

    ``+1`` if ``p, q, r`` turn counter-clockwise, ``-1`` if clockwise, ``0`` if
    collinear.  The floating-point value is trusted only where its own error
    bound proves the sign; otherwise the test is redone in exact arithmetic.
    """
    px, py = p
    qx, qy = q
    rx, ry = r
    left = (px - rx) * (qy - ry)
    right = (py - ry) * (qx - rx)
    det = left - right
    if left > 0.0:
        if right <= 0.0:
            return 1  # true determinant is positive whatever the rounding
        detsum = left + right
    elif left < 0.0:
        if right >= 0.0:
            return -1
        detsum = -left - right
    else:
        detsum = abs(right)
    errbound = _ORIENT_ERRBOUND * detsum
    if det > errbound:
        return 1
    if det < -errbound:
        return -1
    return _orient_exact(p, q, r)


def _orient_exact(p: Point, q: Point, r: Point) -> int:
    """``_orient`` in rational arithmetic (every finite float is exact here)."""
    rx, ry = Fraction(r[0]), Fraction(r[1])
    left = (Fraction(p[0]) - rx) * (Fraction(q[1]) - ry)
    right = (Fraction(p[1]) - ry) * (Fraction(q[0]) - rx)
    return (left > right) - (left < right)


def _bboxes_disjoint(a1: Point, a2: Point, b1: Point, b2: Point) -> bool:
    return (
        max(a1[0], a2[0]) < min(b1[0], b2[0])
        or max(b1[0], b2[0]) < min(a1[0], a2[0])
        or max(a1[1], a2[1]) < min(b1[1], b2[1])
        or max(b1[1], b2[1]) < min(a1[1], a2[1])
    )


def _in_bbox(p: Point, q1: Point, q2: Point) -> bool:
    """Is ``p`` inside the bounding box of ``q1 q2``?

    For a point already known to be collinear with ``q1 q2``, this is exactly
    the test for lying on the segment.
    """
    return (
        min(q1[0], q2[0]) <= p[0] <= max(q1[0], q2[0])
        and min(q1[1], q2[1]) <= p[1] <= max(q1[1], q2[1])
    )


def _point_on_segment(p: Point, q1: Point, q2: Point) -> bool:
    """Full point-on-segment test, without assuming collinearity."""
    return _orient(q1, q2, p) == 0 and _in_bbox(p, q1, q2)


def _collinear_overlap(
    a1: Point, a2: Point, b1: Point, b2: Point
) -> Optional[Union[Point, Segment]]:
    """Overlap of two collinear, non-degenerate segments.

    Along a line, lexicographic ``(x, y)`` order is a total order consistent
    with the line's direction (``x`` is strictly monotone unless the line is
    vertical, in which case ``y`` is), so the overlap can be read straight off
    the sorted endpoints -- no arithmetic, hence no rounding.
    """
    a_lo, a_hi = (a1, a2) if a1 <= a2 else (a2, a1)
    b_lo, b_hi = (b1, b2) if b1 <= b2 else (b2, b1)
    lo = max(a_lo, b_lo)
    hi = min(a_hi, b_hi)
    if lo > hi:
        return None
    if lo == hi:
        return lo
    return (lo, hi)


def _crossing_point(a1: Point, a2: Point, b1: Point, b2: Point) -> Point:
    """Intersection of two non-parallel segments known to cross properly.

    Solved exactly, then rounded once at the end to the nearest float.
    """
    ax, ay = Fraction(a1[0]), Fraction(a1[1])
    rx, ry = Fraction(a2[0]) - ax, Fraction(a2[1]) - ay
    bx, by = Fraction(b1[0]), Fraction(b1[1])
    sx, sy = Fraction(b2[0]) - bx, Fraction(b2[1]) - by
    denom = rx * sy - ry * sx  # non-zero: the caller has ruled out parallels
    t = ((bx - ax) * sy - (by - ay) * sx) / denom
    return (float(ax + t * rx), float(ay + t * ry))