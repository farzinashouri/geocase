"""Oracle for area_m2, ported verbatim from the Step 0 grader."""

from shapely.geometry import Polygon, box

from geocase.benchmark._oracle_utils import GEOD, rel_ok


def build_checks(f):
    def control():
        poly = box(13.0, 52.0, 13.1, 52.1)
        exp, _ = GEOD.geometry_area_perimeter(poly)
        exp = abs(exp)
        got = f(poly)
        return rel_ok(got, exp, 0.01), f"got {got:.4g}, expected {exp:.4g}"

    def dateline():
        # A 2-degree-wide, 1-degree-tall box crossing the antimeridian, as it
        # appears in real data: lons in [-180, 180]. Planar treatment computes
        # the 358-degree-wide complement instead.
        poly = Polygon([(179, 0), (-179, 0), (-179, 1), (179, 1)])
        ref = Polygon([(179, 0), (181, 0), (181, 1), (179, 1)])
        exp, _ = GEOD.geometry_area_perimeter(ref)
        exp = abs(exp)
        got = f(poly)
        return rel_ok(
            got, exp, 0.01
        ), f"got {got:.4g}, expected {exp:.4g} (2x1 deg box)"

    return [
        ("berlin_box", "control", control),
        ("antimeridian_box", "edge", dateline),
    ]
