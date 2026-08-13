"""Oracle for label_point, ported verbatim from the Step 0 grader."""

from shapely.geometry import Polygon, box


def build_checks(f):
    def control():
        poly = box(0, 0, 10, 10)
        p = f(poly)
        return p.within(poly), f"point {p.wkt}"

    def donut():
        poly = Polygon(
            [(0, 0), (10, 0), (10, 10), (0, 10)],
            holes=[[(2, 2), (8, 2), (8, 8), (2, 8)]],
        )
        p = f(poly)
        return p.within(poly), f"point {p.wkt} (centroid lies in the hole)"

    def c_shape():
        poly = Polygon(
            [(0, 0), (10, 0), (10, 10), (0, 10), (0, 8), (8, 8), (8, 2), (0, 2)]
        )
        p = f(poly)
        return p.within(poly), f"point {p.wkt} (centroid lies in the notch)"

    return [
        ("square", "control", control),
        ("donut", "edge", donut),
        ("c_shape", "edge", c_shape),
    ]
