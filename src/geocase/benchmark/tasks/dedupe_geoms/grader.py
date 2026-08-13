"""Oracle for dedupe_geoms (VEC-0013): the same ring with a rotated start
vertex and reversed orientation is a duplicate — WKB hashing misses it."""

from shapely.geometry import Polygon


def build_checks(f):
    def control():
        sq = Polygon([(0, 0), (4, 0), (4, 4), (0, 4)])
        tri = Polygon([(10, 10), (12, 10), (11, 12)])
        got = f([sq, Polygon([(0, 0), (4, 0), (4, 4), (0, 4)]), tri])
        ok = len(got) == 2 and got[0].equals(sq) and got[1].equals(tri)
        return ok, f"kept {len(got)} of 3 (expected 2: square, triangle, in order)"

    def rotated_reversed():
        a = Polygon([(0, 0), (4, 0), (4, 4), (0, 4)])
        b = Polygon([(4, 4), (4, 0), (0, 0), (0, 4)])  # rotated start, reversed
        got = f([a, b])
        ok = len(got) == 1 and got[0].equals(a)
        return ok, (
            f"kept {len(got)} of 2 (same ring, rotated start vertex and "
            "reversed orientation — expected 1)"
        )

    return [
        ("exact_duplicates", "control", control),
        ("rotated_reversed_ring", "edge", rotated_reversed),
    ]
