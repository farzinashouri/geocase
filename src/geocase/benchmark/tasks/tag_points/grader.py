"""Oracle for tag_points (VEC-0012): a point on a shared edge must still be
assigned — `within` silently drops it, an intersects-join duplicates it."""

from shapely.geometry import box

POLYGONS = [box(0, 0, 5, 10), box(5, 0, 10, 10)]  # share the edge x=5


def build_checks(f):
    def control():
        got = f([(2, 2), (7, 3), (20, 20)], POLYGONS)
        exp = [0, 1, None]
        return list(got) == exp, f"got {list(got)!r}, expected {exp!r}"

    def shared_edge():
        got = f([(5, 5)], POLYGONS)
        return list(got) == [0], (
            f"got {list(got)!r}, expected [0] "
            "(point on the shared edge; smallest containing index wins)"
        )

    return [
        ("interior_points", "control", control),
        ("point_on_shared_edge", "edge", shared_edge),
    ]
