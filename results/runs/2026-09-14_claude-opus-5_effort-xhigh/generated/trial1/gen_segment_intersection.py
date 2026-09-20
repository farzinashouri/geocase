"""Exact intersection of two 2D line segments.

The predicate arithmetic is done in exact rational arithmetic
(``fractions.Fraction``, which represents any finite float exactly), so the
orientation and overlap tests are never wrong: there is no epsilon to tune and
no chance of a "sometimes parallel, sometimes crossing" answer for the same
input. The only rounding happens when the exact result is converted back to
float for the return value, and endpoints of the inputs round-trip exactly.

Importing this module has no side effects.
"""

from __future__ import annotations

from fractions import Fraction
from math import isfinite

__all__ = ["segment_intersection"]

Point = tuple[float, float]
Segment = tuple[Point, Point]

_Vec = tuple[Fraction, Fraction]


def _as_exact(pt: object, label: str) -> _Vec:
    """Convert ``(x, y)`` to a pair of exact Fractions."""
    x, y = pt  # type: ignore[misc]
    x = float(x)
    y = float(y)
    if not (isfinite(x) and isfinite(y)):
        raise ValueError(f"{label} has a non-finite coordinate: {pt!r}")
    return Fraction(x), Fraction(y)


def _cross(u: _Vec, v: _Vec) -> Fraction:
    return u[0] * v[1] - u[1] * v[0]


def _dot(u: _Vec, v: _Vec) -> Fraction:
    return u[0] * v[0] + u[1] * v[1]


def _sub(u: _Vec, v: _Vec) -> _Vec:
    return u[0] - v[0], u[1] - v[1]


def _at(origin: _Vec, d: _Vec, t: Fraction) -> Point:
    """Point ``origin + t * d``, rounded to float."""
    return float(origin[0] + t * d[0]), float(origin[1] + t * d[1])


def _covers(origin: _Vec, d: _Vec, pt: _Vec) -> bool:
    """True if ``pt`` lies on the segment ``origin -> origin + d`` (d non-zero)."""
    w = _sub(pt, origin)
    if _cross(w, d) != 0:
        return False
    return 0 <= _dot(w, d) <= _dot(d, d)


def segment_intersection(a, b):
    """Intersect two closed 2D segments in a planar coordinate system.

    Each argument is ``((x1, y1), (x2, y2))``. Degenerate (zero-length)
    segments are accepted and treated as the single point they describe.

    Returns:
        ``None`` if the segments share no point;
        ``(x, y)`` if they share exactly one point;
        ``((xa, ya), (xb, yb))`` if they share more than one point, i.e. they
        are collinear and overlap. The overlap endpoints are ordered along the
        direction of ``a`` (from ``a[0]`` toward ``a[1]``).

    Raises:
        ValueError: if any coordinate is NaN or infinite.

    Examples:
        >>> segment_intersection(((0, 0), (2, 2)), ((0, 2), (2, 0)))
        (1.0, 1.0)
        >>> segment_intersection(((0, 0), (1, 1)), ((1, 1), (2, 0)))
        (1.0, 1.0)
        >>> segment_intersection(((0, 0), (3, 0)), ((1, 0), (5, 0)))
        ((1.0, 0.0), (3.0, 0.0))
        >>> segment_intersection(((0, 0), (1, 0)), ((0, 1), (1, 1))) is None
        True
    """
    a0, a1 = a
    b0, b1 = b
    p = _as_exact(a0, "a[0]")
    p_end = _as_exact(a1, "a[1]")
    q = _as_exact(b0, "b[0]")
    q_end = _as_exact(b1, "b[1]")

    r = _sub(p_end, p)  # direction of a
    s = _sub(q_end, q)  # direction of b

    a_degenerate = r == (0, 0)
    b_degenerate = s == (0, 0)
    if a_degenerate and b_degenerate:
        return (float(p[0]), float(p[1])) if p == q else None
    if a_degenerate:
        return (float(p[0]), float(p[1])) if _covers(q, s, p) else None
    if b_degenerate:
        return (float(q[0]), float(q[1])) if _covers(p, r, q) else None

    qp = _sub(q, p)
    denom = _cross(r, s)

    if denom != 0:
        # Non-parallel: the supporting lines meet in exactly one point.
        t = _cross(qp, s) / denom
        u = _cross(qp, r) / denom
        if 0 <= t <= 1 and 0 <= u <= 1:
            return _at(p, r, t)
        return None

    if _cross(qp, r) != 0:
        # Parallel with distinct supporting lines.
        return None

    # Collinear: intersect the two parameter intervals on a's line.
    rr = _dot(r, r)
    t0 = _dot(qp, r) / rr
    t1 = t0 + _dot(s, r) / rr
    lo, hi = (t0, t1) if t0 <= t1 else (t1, t0)
    lo = max(lo, Fraction(0))
    hi = min(hi, Fraction(1))

    if lo > hi:
        return None
    if lo == hi:
        return _at(p, r, lo)
    return _at(p, r, lo), _at(p, r, hi)