"""Segment intersection utilities."""


def segment_intersection(a, b):
    (x1, y1), (x2, y2) = a
    (x3, y3), (x4, y4) = b

    dax, day = x2 - x1, y2 - y1
    dbx, dby = x4 - x3, y4 - y3

    denom = dax * dby - day * dbx

    def on_segment(px, py, sx1, sy1, sx2, sy2, eps=1e-12):
        cross = (px - sx1) * (sy2 - sy1) - (py - sy1) * (sx2 - sx1)
        if abs(cross) > eps:
            return False
        dot = (px - sx1) * (sx2 - sx1) + (py - sy1) * (sy2 - sy1)
        sq_len = (sx2 - sx1) ** 2 + (sy2 - sy1) ** 2
        return -eps <= dot <= sq_len + eps

    if abs(denom) > 1e-12:
        dx, dy = x3 - x1, y3 - y1
        t = (dx * dby - dy * dbx) / denom
        u = (dx * day - dy * dax) / denom
        eps = 1e-9
        if -eps <= t <= 1 + eps and -eps <= u <= 1 + eps:
            px = x1 + t * dax
            py = y1 + t * day
            return (px, py)
        return None

    cross = dax * (y3 - y1) - day * (x3 - x1)
    if abs(cross) > 1e-9:
        return None

    len_a_sq = dax * dax + day * day
    if len_a_sq < 1e-24:
        if on_segment(x1, y1, x3, y3, x4, y4):
            return (x1, y1)
        return None

    def project(px, py):
        return ((px - x1) * dax + (py - y1) * day) / len_a_sq

    t0 = 0.0
    t1 = 1.0
    t2 = project(x3, y3)
    t3 = project(x4, y4)

    lo_b, hi_b = min(t2, t3), max(t2, t3)
    lo = max(t0, lo_b)
    hi = min(t1, hi_b)

    eps = 1e-9
    if lo > hi + eps:
        return None

    def point_at(t):
        return (x1 + t * dax, y1 + t * day)

    if abs(hi - lo) <= eps:
        return point_at(lo)

    pa = point_at(lo)
    pb = point_at(hi)
    return (pa, pb)