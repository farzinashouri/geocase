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

    def battery(ring, ref_ring):
        # Same test, other places: the ring jumps across the antimeridian, the
        # reference is the same ring with longitudes unwrapped past 180.
        def check():
            exp = abs(GEOD.geometry_area_perimeter(Polygon(ref_ring))[0])
            got = f(Polygon(ring))
            return rel_ok(got, exp, 0.01), f"got {got:.4g}, expected {exp:.4g}"

        return check

    return [
        ("berlin_box", "control", control),
        ("antimeridian_box", "edge", dateline),
        (
            "antimeridian_westward",
            "edge",
            battery(
                [(-178, 10), (178, 10), (178, 12), (-178, 12)],
                [(-178, 10), (-182, 10), (-182, 12), (-178, 12)],
            ),
        ),
        (
            "pole_adjacent_crossing",
            "edge",
            battery(
                [(175, 80), (-175, 80), (-175, 85), (175, 85)],
                [(175, 80), (185, 80), (185, 85), (175, 85)],
            ),
        ),
        (
            "equator_crossing",
            "edge",
            battery(
                [(179.5, -1), (-179.5, -1), (-179.5, 1), (179.5, 1)],
                [(179.5, -1), (180.5, -1), (180.5, 1), (179.5, 1)],
            ),
        ),
        (
            "southern_hemisphere",
            "edge",
            battery(
                [(-179.5, -60), (179.5, -60), (179.5, -58), (-179.5, -58)],
                [(-179.5, -60), (-180.5, -60), (-180.5, -58), (-179.5, -58)],
            ),
        ),
    ]
