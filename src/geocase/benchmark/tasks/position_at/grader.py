"""Oracle for position_at, ported verbatim from the Step 0 grader."""


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

    return [
        ("quarter_along_leg", "control", control),
        ("leg_across_dateline", "edge", dateline),
    ]
