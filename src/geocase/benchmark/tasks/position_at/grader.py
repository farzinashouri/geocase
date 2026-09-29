"""Oracle for position_at, ported verbatim from the Step 0 grader."""

from geocase.benchmark._oracle_utils import GEOD


def build_checks(f):
    def control():
        lon, lat = f([(0, 5.0, 50.0), (3600, 5.2, 50.2)], 900)
        ok = abs(lon - 5.05) < 0.01 and abs(lat - 50.05) < 0.01
        return ok, f"got ({lon:.4f}, {lat:.4f}), expected ~(5.05, 50.05)"

    def dateline():
        lon, lat = f([(0, 179.5, 10.0), (3600, -179.5, 10.2)], 1800)
        ok = abs(abs(lon) - 180.0) < 0.15 and 10.05 < lat < 10.15
        return ok, (
            f"got ({lon:.4f}, {lat:.4f}), "
            "expected lon near +/-180 (ship crosses the dateline)"
        )

    def battery(fixes, t):
        # The ship sails the geodesic between the two fixes at constant speed.
        # Accept anything within 5 % of the leg length of that position.
        def check():
            (_, lon1, lat1), (_, lon2, lat2) = fixes[0], fixes[-1]
            az, _, leg = GEOD.inv(lon1, lat1, lon2, lat2)
            frac = (t - fixes[0][0]) / (fixes[-1][0] - fixes[0][0])
            exp_lon, exp_lat, _ = GEOD.fwd(lon1, lat1, az, leg * frac)
            lon, lat = f(fixes, t)
            off = GEOD.inv(lon, lat, exp_lon, exp_lat)[2]
            return off <= 0.05 * leg, (
                f"got ({lon:.4f}, {lat:.4f}), expected ~({exp_lon:.4f}, "
                f"{exp_lat:.4f}); {off / 1000:.1f} km off on a {leg / 1000:.0f} km leg"
            )

        return check

    return [
        ("quarter_along_leg", "control", control),
        ("leg_across_dateline", "edge", dateline),
        (
            "dateline_westward",
            "edge",
            battery([(0, -179.5, 10.0), (3600, 179.5, 10.2)], 1800),
        ),
        (
            "pole_adjacent",
            "edge",
            battery([(0, 170.0, 85.0), (3600, -170.0, 85.0)], 900),
        ),
        (
            "equator_crossing",
            "edge",
            battery([(0, 179.8, -0.3), (3600, -179.8, 0.3)], 1800),
        ),
        (
            "southern_hemisphere",
            "edge",
            battery([(0, -179.5, -60.0), (3600, 179.5, -59.8)], 2700),
        ),
    ]
