"""Intersection of two 2D line segments."""

_EPS = 1e-9


def _cross(o, p, q):
    """Cross product of vectors (p - o) and (q - o)."""
    return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])


def _dot(u, v):
    return u[0] * v[0] + u[1] * v[1]


def _magnitude_scale(*points):
    vals = [abs(c) for p in points for c in p]
    return max(vals + [1.0])


def _point_on_segment(p, seg, eps_coord, eps_t):
    (x1, y1), (x2, y2) = seg
    dx, dy = x2 - x1, y2 - y1
    if abs(dx) < eps_coord and abs(dy) < eps_coord:
        if abs(p[0] - x1) < eps_coord and abs(p[1] - y1) < eps_coord:
            return (x1, y1)
        return None
    area2 = (p[0] - x1) * dy - (p[1] - y1) * dx
    if abs(area2) > eps_coord * max(abs(dx), abs(dy), 1.0):
        return None
    dd = dx * dx + dy * dy
    t = ((p[0] - x1) * dx + (p[1] - y1) * dy) / dd
    if -eps_t <= t <= 1 + eps_t:
        t = min(max(t, 0.0), 1.0)
        return (x1 + t * dx, y1 + t * dy)
    return None


def segment_intersection(a, b):
    (ax1, ay1), (ax2, ay2) = a
    (bx1, by1), (bx2, by2) = b

    scale = _magnitude_scale((ax1, ay1), (ax2, ay2), (bx1, by1), (bx2, by2))
    eps_coord = _EPS * scale
    eps_area = _EPS * scale * scale
    eps_t = _EPS

    dax, day = ax2 - ax1, ay2 - ay1
    dbx, dby = bx2 - bx1, by2 - by1

    a_is_point = abs(dax) < eps_coord and abs(day) < eps_coord
    b_is_point = abs(dbx) < eps_coord and abs(dby) < eps_coord

    if a_is_point and b_is_point:
        if abs(ax1 - bx1) < eps_coord and abs(ay1 - by1) < eps_coord:
            return (ax1, ay1)
        return None

    if a_is_point:
        return _point_on_segment((ax1, ay1), b, eps_coord, eps_t)

    if b_is_point:
        return _point_on_segment((bx1, by1), a, eps_coord, eps_t)

    denom = dby * dax - dbx * day

    if abs(denom) > eps_area:
        ta = (dbx * (ay1 - by1) - dby * (ax1 - bx1)) / denom
        tb = (dax * (ay1 - by1) - day * (ax1 - bx1)) / denom
        if -eps_t <= ta <= 1 + eps_t and -eps_t <= tb <= 1 + eps_t:
            ta = min(max(ta, 0.0), 1.0)
            return (ax1 + ta * dax, ay1 + ta * day)
        return None

    # Directions are parallel; check whether the lines are collinear.
    if abs(_cross((ax1, ay1), (ax2, ay2), (bx1, by1))) > eps_area:
        return None

    # Collinear: project b's endpoints onto a's direction and overlap ranges.
    dd = _dot((dax, day), (dax, day))
    tb1 = _dot((bx1 - ax1, by1 - ay1), (dax, day)) / dd
    tb2 = _dot((bx2 - ax1, by2 - ay1), (dax, day)) / dd

    lo_b, hi_b = min(tb1, tb2), max(tb1, tb2)
    lo = max(0.0, lo_b)
    hi = min(1.0, hi_b)

    if lo > hi + eps_t:
        return None

    if abs(hi - lo) <= eps_t:
        t = (lo + hi) / 2.0
        return (ax1 + t * dax, ay1 + t * day)

    p1 = (ax1 + lo * dax, ay1 + lo * day)
    p2 = (ax1 + hi * dax, ay1 + hi * day)
    return (p1, p2)