"""Planar segment–segment intersection.

Computes the common part of two 2-D line segments.  The result is one of

* ``None``                       -- the segments share no point,
* ``(x, y)``                     -- the segments share exactly one point,
* ``((xa, ya), (xb, yb))``       -- the segments overlap along a sub-segment.

Only the standard library is used, so importing this module is free of side
effects and of third-party dependencies.

Robustness
----------
Coordinates are floats, so "do the segments touch?" cannot be answered by
exact comparisons alone.  Every decision in this module is therefore taken
against a single absolute distance tolerance ``eps``, derived from a relative
tolerance and the magnitude of the coordinates involved::

    eps = rel_tol * max(|coordinate|, 1.0)

Two points closer than ``eps`` are treated as the same point, a point within
``eps`` of a line is treated as lying on it, and a segment shorter than
``eps`` is treated as degenerate (a single point).  Callers working in a
projected CRS with metre units and a tolerance in mind (say 1 mm) can pass
``rel_tol`` accordingly.
"""

from __future__ import annotations

from math import hypot, isfinite

__all__ = ["segment_intersection", "DEFAULT_REL_TOL"]

#: Relative tolerance used when none is supplied; a few ulps of double
#: precision, enough to absorb rounding in the cross products below.
DEFAULT_REL_TOL = 1e-12


def segment_intersection(a, b, *, rel_tol=DEFAULT_REL_TOL):
    """Return the intersection of segments ``a`` and ``b``.

    Parameters
    ----------
    a, b : ``((x1, y1), (x2, y2))``
        The segments, in any planar coordinate system.  Degenerate segments
        (both endpoints equal) are accepted and behave as points.
    rel_tol : float, optional
        Relative tolerance, see the module docstring.

    Returns
    -------
    None, ``(x, y)`` or ``((xa, ya), (xb, yb))``
        ``None`` when the segments are disjoint, a point when they meet in
        exactly one place, and a segment when they overlap.  An overlap is
        reported oriented along ``a``: ``(xa, ya)`` is the end nearer to
        ``a``'s first endpoint.

    Raises
    ------
    ValueError
        If a segment is malformed or holds a non-finite coordinate.
    """
    p1x, p1y, p2x, p2y = _unpack(a, "a")
    q1x, q1y, q2x, q2y = _unpack(b, "b")

    rel_tol = float(rel_tol)
    if not isfinite(rel_tol) or rel_tol < 0.0:
        raise ValueError("rel_tol must be a finite, non-negative number")

    scale = max(abs(p1x), abs(p1y), abs(p2x), abs(p2y),
                abs(q1x), abs(q1y), abs(q2x), abs(q2y), 1.0)
    eps = rel_tol * scale

    rx, ry = p2x - p1x, p2y - p1y
    sx, sy = q2x - q1x, q2y - q1y
    len_r = hypot(rx, ry)
    len_s = hypot(sx, sy)

    # --- degenerate inputs -------------------------------------------------
    if len_r <= eps and len_s <= eps:
        if hypot(q1x - p1x, q1y - p1y) <= eps:
            return (0.5 * (p1x + q1x), 0.5 * (p1y + q1y))
        return None
    if len_r <= eps:
        return (p1x, p1y) if _near_segment(p1x, p1y, q1x, q1y, sx, sy, len_s, eps) else None
    if len_s <= eps:
        return (q1x, q1y) if _near_segment(q1x, q1y, p1x, p1y, rx, ry, len_r, eps) else None

    qpx, qpy = q1x - p1x, q1y - p1y
    denom = rx * sy - ry * sx

    # --- the general, transversal case -------------------------------------
    # ``|denom| / (len_r * len_s)`` is the sine of the angle between the
    # segments; comparing it to rel_tol keeps the test scale-free.
    if abs(denom) > rel_tol * len_r * len_s:
        t = (qpx * sy - qpy * sx) / denom
        u = (qpx * ry - qpy * rx) / denom
        # Translate the distance tolerance into each parameter space so that
        # an endpoint grazing the other segment still counts as a touch.
        if not (-eps / len_r <= t <= 1.0 + eps / len_r):
            return None
        if not (-eps / len_s <= u <= 1.0 + eps / len_s):
            return None
        t = _clamp01(t)
        return (p1x + t * rx, p1y + t * ry)

    # --- parallel: collinear or disjoint ------------------------------------
    if abs(qpx * ry - qpy * rx) / len_r > eps:
        return None  # parallel but offset

    # Collinear.  Express b's endpoints in a's parameter space and intersect
    # the two intervals.
    rr = rx * rx + ry * ry
    t0 = (qpx * rx + qpy * ry) / rr
    t1 = t0 + (sx * rx + sy * ry) / rr
    if t1 < t0:
        t0, t1 = t1, t0

    lo = t0 if t0 > 0.0 else 0.0
    hi = t1 if t1 < 1.0 else 1.0
    t_eps = eps / len_r

    if hi < lo - t_eps:
        return None
    if hi <= lo + t_eps:
        t = _clamp01(0.5 * (lo + hi))
        return (p1x + t * rx, p1y + t * ry)
    return ((p1x + lo * rx, p1y + lo * ry),
            (p1x + hi * rx, p1y + hi * ry))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _unpack(seg, name):
    """Validate one segment and return its four float coordinates."""
    try:
        (x1, y1), (x2, y2) = seg
        coords = (float(x1), float(y1), float(x2), float(y2))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"segment {name} must be ((x1, y1), (x2, y2)) of numbers, got {seg!r}"
        ) from exc
    if not all(isfinite(c) for c in coords):
        raise ValueError(f"segment {name} has a non-finite coordinate: {seg!r}")
    return coords


def _near_segment(px, py, ox, oy, dx, dy, length, eps):
    """True when point ``(px, py)`` lies within ``eps`` of a segment.

    The segment starts at ``(ox, oy)`` with direction ``(dx, dy)`` and the
    given (non-zero) ``length``.
    """
    t = ((px - ox) * dx + (py - oy) * dy) / (length * length)
    t = _clamp01(t)
    return hypot(px - (ox + t * dx), py - (oy + t * dy)) <= eps


def _clamp01(t):
    """Clamp a curve parameter to ``[0, 1]``."""
    if t < 0.0:
        return 0.0
    if t > 1.0:
        return 1.0
    return t