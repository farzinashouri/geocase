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
        # covers() is only meaningful on a valid geometry; asking an invalid
        # one produces arbitrary answers, so the validity gate comes first.
        both_lobes = (
            got.is_valid and got.covers(Point(2, 5)) and got.covers(Point(8, 5))
        )
        ok = got.is_valid and both_lobes and rel_ok(got.area, 50.0, 0.01)
        return ok, (
            f"valid={got.is_valid}, area {got.area:.4g} (expected 50), "
            f"both_lobes={both_lobes} (buffer(0) keeps only one)"
        )

    def _both_lobes(poly, expected_area, lobe_points, label):
        got = f(poly)
        keeps = got.is_valid and all(got.covers(Point(p)) for p in lobe_points)
        ok = keeps and rel_ok(got.area, expected_area, 0.01)
        return ok, (
            f"valid={got.is_valid}, area {got.area:.4g} "
            f"(expected {expected_area:.4g}), both_lobes={keeps} ({label})"
        )

    def bowtie_southern():
        # The 10x10 bowtie moved to (-120, -30): same two 25-unit lobes.
        dx, dy = -120, -30
        pts = [(0, 0), (10, 10), (10, 0), (0, 10)]
        poly = Polygon([(x + dx, y + dy) for x, y in pts])
        return _both_lobes(
            poly, 50.0, [(2 + dx, 5 + dy), (8 + dx, 5 + dy)], "translated bowtie"
        )

    def bowtie_tiny():
        # Degree-scale bowtie 1e-3 wide: lobes of 25e-6 each.
        s = 1e-3
        poly = Polygon([(0, 0), (10 * s, 10 * s), (10 * s, 0), (0, 10 * s)])
        return _both_lobes(
            poly, 50.0 * s * s, [(2 * s, 5 * s), (8 * s, 5 * s)], "tiny coordinates"
        )

    def bowtie_unequal_lobes():
        # Edges (0,0)-(10,10) and (10,0)-(2,8) cross at (5,5): the lobes are
        # triangles (0,0),(5,5),(2,8) = 15 and (5,5),(10,10),(10,0) = 25.
        poly = Polygon([(0, 0), (10, 10), (10, 0), (2, 8)])
        return _both_lobes(
            poly, 40.0, [(7 / 3, 13 / 3), (25 / 3, 5)], "lobes of 15 and 25"
        )

    return [
        ("valid_input_unchanged", "control", control),
        ("bowtie_keeps_both_lobes", "edge", bowtie),
        ("bowtie_southern_offset", "edge", bowtie_southern),
        ("bowtie_tiny_coordinates", "edge", bowtie_tiny),
        ("bowtie_unequal_lobes", "edge", bowtie_unequal_lobes),
    ]
