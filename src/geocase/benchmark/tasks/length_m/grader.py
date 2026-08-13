"""Oracle for length_m, ported verbatim from the Step 0 grader."""

from shapely.geometry import LineString

from geocase.benchmark._oracle_utils import GEOD, rel_ok


def build_checks(f):
    def control():
        line = LineString([(0, 0), (1, 0)])
        exp = GEOD.geometry_length(line)
        got = f(line)
        return rel_ok(got, exp, 0.005), f"got {got:.6g}, expected {exp:.6g}"

    def lat60():
        line = LineString([(0, 60), (1, 60)])
        exp = GEOD.geometry_length(line)  # ~55.8 km, not 111.32 km
        got = f(line)
        return rel_ok(got, exp, 0.005), f"got {got:.6g}, expected {exp:.6g}"

    def dateline():
        line = LineString([(179.5, 0), (-179.5, 0)])
        exp = GEOD.geometry_length(line)  # shortest path: ~111.3 km, not 359 deg
        got = f(line)
        return rel_ok(got, exp, 0.005), f"got {got:.6g}, expected {exp:.6g}"

    return [
        ("1deg_equator", "control", control),
        ("1deg_at_lat60", "edge", lat60),
        ("1deg_across_dateline", "edge", dateline),
    ]
