"""Exact-ish intersection of two 2D line segments in a planar coordinate system.

The module is dependency-free (standard library only) and has no import-time
side effects.

Public API
----------
segment_intersection(a, b)
    Return ``None``, a point ``(x, y)``, or a segment ``((xa, ya), (xb, yb))``.
"""

from __future__ import annotations

__all__ = ["segment_intersection"]

# Relative tolerance used to decide whether a cross product / parameter is zero.
# Every comparison below is scaled by the magnitude of the coordinates involved,
# so the function behaves the same for metre-scale and degree-scale inputs.
_REL_EPS = 1e-12


def _sub(p, q):
    return (p[0] - q[0], p[1] - q[1])


def _cross(u, v):
    return u[0] * v[1] - u[1] * v[0]


def _dot(u, v):
    return u[0] * v[0] + u[1] * v[1]


def _lerp(p, d, t):
    return (p[0] + d[0] * t, p[1] + d[1] * t)


def _coords(seg):
    (x1, y1), (x2, y2) = seg
    return (float(x1), float(y1)), (float(x2), float(y2))


def _scale(*points):
    """Characteristic magnitude of a set of points (never zero)."""
    m = 1.0
    for x, y in points:
        m = max(m, abs(x), abs(y))
    return m


def _same_point(p, q, eps):
    return abs(p[0] - q[0]) <= eps and abs(p[1] - q[1]) <= eps


def _point_on_segment(pt, seg, eps_len):
    """True if ``pt`` lies on the (possibly degenerate) segment ``seg``."""
    p, q = seg
    d = _sub(q, p)
    w = _sub(pt, p)
    dd = _dot(d, d)
    if dd == 0.0:
        return _same_point(pt, p, eps_len)
    # Perpendicular distance test, written as a cross product scaled by length.
    if abs(_cross(d, w)) > eps_len * (dd ** 0.5):
        return False
    t = _dot(w, d) / dd
    tol = eps_len / (dd ** 0.5)
    return -tol <= t <= 1.0 + tol


def segment_intersection(a, b):
    """Intersect two 2D segments.

    Parameters
    ----------
    a, b : ((x1, y1), (x2, y2))
        Segment endpoints with float coordinates in a planar system.

    Returns
    -------
    None
        The segments share no point.
    (x, y)
        The segments share exactly one point.
    ((xa, ya), (xb, yb))
        The segments overlap along a sub-segment; its endpoints are returned.
    """
    p1, p2 = _coords(a)
    q1, q2 = _coords(b)

    scale = _scale(p1, p2, q1, q2)
    eps_len = _REL_EPS * scale          # tolerance on a length
    eps_area = _REL_EPS * scale * scale  # tolerance on a cross product

    r = _sub(p2, p1)
    s = _sub(q2, q1)
    a_degenerate = abs(r[0]) <= 0.0 and abs(r[1]) <= 0.0
    b_degenerate = abs(s[0]) <= 0.0 and abs(s[1]) <= 0.0

    # --- degenerate (point) inputs ---------------------------------------
    if a_degenerate and b_degenerate:
        return p1 if _same_point(p1, q1, eps_len) else None
    if a_degenerate:
        return p1 if _point_on_segment(p1, (q1, q2), eps_len) else None
    if b_degenerate:
        return q1 if _point_on_segment(q1, (p1, p2), eps_len) else None

    denom = _cross(r, s)
    qp = _sub(q1, p1)

    # --- parallel / collinear --------------------------------------------
    if abs(denom) <= eps_area:
        if abs(_cross(qp, r)) > eps_area:
            return None  # parallel but distinct supporting lines

        # Collinear: project both segments onto the direction of ``a``.
        rr = _dot(r, r)
        t0 = _dot(qp, r) / rr
        t1 = _dot(_sub(q2, p1), r) / rr
        lo, hi = (t0, t1) if t0 <= t1 else (t1, t0)

        tol = eps_len / (rr ** 0.5)
        start = max(0.0, lo)
        end = min(1.0, hi)
        if start > end + tol:
            return None
        if abs(end - start) <= tol:
            return _lerp(p1, r, (start + end) / 2.0)
        return (_lerp(p1, r, start), _lerp(p1, r, end))

    # --- proper (single point) intersection -------------------------------
    t = _cross(qp, s) / denom
    u = _cross(qp, r) / denom

    t_tol = eps_len / (_dot(r, r) ** 0.5)
    u_tol = eps_len / (_dot(s, s) ** 0.5)
    if -t_tol <= t <= 1.0 + t_tol and -u_tol <= u <= 1.0 + u_tol:
        t = min(1.0, max(0.0, t))
        return _lerp(p1, r, t)
    return None