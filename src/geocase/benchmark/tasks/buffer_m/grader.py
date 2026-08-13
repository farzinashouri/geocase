"""Oracle for buffer_m, ported verbatim from the Step 0 grader."""

from shapely.geometry import Point

from geocase.benchmark._oracle_utils import GEOD


def build_checks(f):
    def control():
        buf = f(Point(10, 50), 1000)
        lon_in, lat_in, _ = GEOD.fwd(10, 50, 90, 900)
        lon_out, lat_out, _ = GEOD.fwd(10, 50, 90, 1100)
        ok = (
            buf.is_valid
            and buf.intersects(Point(lon_in, lat_in))
            and not buf.intersects(Point(lon_out, lat_out))
        )
        return (
            ok,
            f"valid={buf.is_valid}, 900m in={buf.intersects(Point(lon_in, lat_in))}",
        )

    def dateline():
        buf = f(Point(179.9, 0), 50_000)
        # ~33.4 km east of the center, on the other side of the antimeridian.
        across = buf.intersects(Point(-179.8, 0)) or buf.intersects(Point(180.2, 0))
        # ~211 km west: must be outside.
        far = buf.intersects(Point(178.0, 0))
        w, _, e, _ = buf.bounds
        wrapped_world = (e - w) > 300  # bowtie smeared across the world
        ok = buf.is_valid and across and not far and not wrapped_world
        return ok, (
            f"valid={buf.is_valid}, across_dateline={across}, "
            f"contains_far_point={far}, lon_span={e - w:.1f}"
        )

    return [
        ("1km_at_lat50", "control", control),
        ("50km_across_dateline", "edge", dateline),
    ]
