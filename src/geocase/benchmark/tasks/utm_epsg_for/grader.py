"""Oracle for utm_epsg_for, ported verbatim from the Step 0 grader."""


def build_checks(f):
    cases = [
        ("berlin", "control", (13.4, 52.5), 32633),
        ("buenos_aires_south", "control", (-58.4, -34.6), 32721),
        # Svalbard: zone 33X spans 9E-21E above 72N; the lon/6 formula says 32.
        ("svalbard_33X", "edge", (10.5, 78.0), 32633),
        # SW Norway: 32V is widened to 3E-12E between 56N and 64N; formula says 31.
        ("norway_32V", "edge", (4.5, 60.0), 32632),
    ]

    def make(lon, lat, exp):
        def chk():
            got = f(lon, lat)
            return int(got) == exp, f"got {got}, expected {exp}"

        return chk

    return [(name, kind, make(lon, lat, exp)) for name, kind, (lon, lat), exp in cases]
