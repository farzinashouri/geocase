"""Oracle for tag_points (VEC-0012): a point on a shared edge must still be
assigned — `within` silently drops it, an intersects-join duplicates it."""

from shapely.geometry import Polygon, box

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

    def outer_boundary():
        got = f([(0, 5), (10, 5)], POLYGONS)
        return list(got) == [0, 1], (
            f"got {list(got)!r}, expected [0, 1] (points on the outer boundary)"
        )

    def corner_vertices():
        got = f([(5, 0), (5, 10), (10, 10)], POLYGONS)
        return list(got) == [0, 0, 1], (
            f"got {list(got)!r}, expected [0, 0, 1] (shared and outer corners)"
        )

    def hole_boundary():
        donut = Polygon(
            [(0, 0), (10, 0), (10, 10), (0, 10)],
            holes=[[(2, 2), (8, 2), (8, 8), (2, 8)]],
        )
        got = f([(2, 5), (5, 5)], [donut])
        return list(got) == [0, None], (
            f"got {list(got)!r}, expected [0, None] "
            "(the hole's edge belongs to the polygon; its interior does not)"
        )

    return [
        ("interior_points", "control", control),
        ("point_on_shared_edge", "edge", shared_edge),
        ("point_on_outer_boundary", "edge", outer_boundary),
        ("point_on_corner_vertex", "edge", corner_vertices),
        ("point_on_hole_boundary", "edge", hole_boundary),
    ]
