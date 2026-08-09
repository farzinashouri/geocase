"""Oracle for voronoi_cells, ported verbatim from the Step 0 grader."""

from shapely.geometry import Point

from geocase.benchmark._oracle_utils import rel_ok

PTS = [(1, 1), (9, 2), (4, 7), (2, 9), (8, 8)]
BOUNDS = (0, 0, 10, 10)


def build_checks(f):
    def partition():
        cells = f(PTS, BOUNDS)
        total = sum(c.area for c in cells)
        ok = len(cells) == len(PTS) and rel_ok(total, 100.0, 0.01)
        return ok, f"{len(cells)} cells, total area {total:.3f}"

    def order():
        cells = f(PTS, BOUNDS)
        misses = [
            i for i, (c, p) in enumerate(zip(cells, PTS)) if not c.contains(Point(p))
        ]
        return not misses, (
            f"cells not containing their own point: {misses or 'none'} "
            "(cell order must match input point order)"
        )

    return [
        ("partition_of_bounds", "control", partition),
        ("cell_order_matches_input", "edge", order),
    ]
