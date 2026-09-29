"""Oracle for buffer_m, ported verbatim from the Step 0 grader."""

from shapely.geometry import LineString, Point

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

    def battery(geom, distance, origins):
        # Each origin is (lon, lat, azimuth) on the geometry's outline. The
        # buffer must contain the point 0.9 x distance beyond it and must not
        # contain the one 1.1 x distance beyond it; a longitude is matched
        # whichever side of the antimeridian the answer represents it on.
        def hit(buf, lon, lat):
            return any(buf.intersects(Point(lon + k, lat)) for k in (-360, 0, 360))

        def check():
            buf = f(geom, distance)
            missed, leaked = [], []
            for lon, lat, az in origins:
                near = GEOD.fwd(lon, lat, az, 0.9 * distance)[:2]
                far = GEOD.fwd(lon, lat, az, 1.1 * distance)[:2]
                if not hit(buf, *near):
                    missed.append(az)
                if hit(buf, *far):
                    leaked.append(az)
            parts = getattr(buf, "geoms", [buf])
            span = max(p.bounds[2] - p.bounds[0] for p in parts)
            ok = buf.is_valid and not missed and not leaked and span < 300
            return ok, (
                f"valid={buf.is_valid}, missed_inside_at={missed}, "
                f"leaked_outside_at={leaked}, max_part_lon_span={span:.1f}"
            )

        return check

    def around(lon, lat):
        return [(lon, lat, az) for az in (0, 90, 180, 270)]

    return [
        ("1km_at_lat50", "control", control),
        ("50km_across_dateline", "edge", dateline),
        (
            "dateline_westward",
            "edge",
            battery(Point(-179.9, 0), 50_000, around(-179.9, 0)),
        ),
        (
            "pole_adjacent",
            "edge",
            battery(Point(179.5, 85), 100_000, around(179.5, 85)),
        ),
        (
            "equator_crossing_line",
            "edge",
            battery(
                LineString([(179.9, -0.5), (179.9, 0.5)]),
                30_000,
                [(179.9, 0, 90), (179.9, 0, 270), (179.9, 0.5, 0), (179.9, -0.5, 180)],
            ),
        ),
        (
            "southern_hemisphere",
            "edge",
            battery(Point(-179.9, -60), 80_000, around(-179.9, -60)),
        ),
    ]
