"""Oracle for tile_bounds, ported verbatim from the Step 0 grader."""

from geocase.benchmark._oracle_utils import xyz_tile_bounds


def build_checks(f):
    def control():
        got = f(0, 0, 0)
        exp = xyz_tile_bounds(0, 0, 0)
        ok = all(abs(g - e) < 1e-6 for g, e in zip(got, exp))
        return ok, f"got {got}"

    def tms_flip():
        # TMS row 1 at z=2 is XYZ row 2 (southern hemisphere band 0..-66.5).
        got = f(2, 1, 1)
        exp = xyz_tile_bounds(2, 1, 2)
        ok = all(abs(g - e) < 1e-6 for g, e in zip(got, exp))
        return ok, (
            f"got {tuple(round(v, 4) for v in got)}, "
            f"expected {tuple(round(v, 4) for v in exp)}"
        )

    return [
        ("z0_world", "control", control),
        ("z2_tms_row_flip", "edge", tms_flip),
    ]
