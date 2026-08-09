"""Oracle for fix_geometry (VEC-0014): repairing a bowtie must keep both
lobes — `buffer(0)` quietly deletes one. Expected areas are first-principles:
the bowtie's rings enclose two 25-unit triangles."""

from shapely.geometry import Point, Polygon

from geocase.benchmark._oracle_utils import rel_ok


def build_checks(f):
    def control():
        poly = Polygon([(0, 0), (10, 0), (10, 4), (4, 4), (4, 10), (0, 10)])
        got = f(poly)
        ok = got.is_valid and rel_ok(got.area, poly.area, 1e-9)
        return (
            ok,
            f"valid={got.is_valid}, area {got.area:.4g} (expected {poly.area:.4g})",
        )

    def bowtie():
        # Self-crossing ring: two triangular lobes meeting at (5,5), 25 each.
        poly = Polygon([(0, 0), (10, 10), (10, 0), (0, 10)])
        got = f(poly)
        both_lobes = got.covers(Point(2, 5)) and got.covers(Point(8, 5))
        ok = got.is_valid and both_lobes and rel_ok(got.area, 50.0, 0.01)
        return ok, (
            f"valid={got.is_valid}, area {got.area:.4g} (expected 50), "
            f"both_lobes={both_lobes} (buffer(0) keeps only one)"
        )

    return [
        ("valid_input_unchanged", "control", control),
        ("bowtie_keeps_both_lobes", "edge", bowtie),
    ]
