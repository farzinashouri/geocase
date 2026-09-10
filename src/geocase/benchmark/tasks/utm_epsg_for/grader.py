"""Oracle for utm_epsg_for, ported from the Step 0 grader.

The expected codes for the two edge points are the MGRS grid-zone exceptions,
which the prompt names as the zone-assignment standard (Plan 46 §0.2). They
are **not** what EPSG's areas of use encode: ``pyproj.query_utm_crs_info``
returns 32632 for (10.5, 78) and 32631 for (4.5, 60) — the plain 6-degree
slices — as ``tests/benchmark/agent_baseline/RESULTS.md`` records. Under the
old prompt ("the CRS appropriate for that location") both answers were
defensible and one was scored SILENT; the prompt now pins the standard, so a
pyproj-delegating answer is wrong for a stated reason.
"""

# Hand-typed, and therefore cited: see SOURCES.
ZONE_EXCEPTIONS = {
    # Svalbard: zone 33X spans 9E-21E above 72N; the lon/6 formula says 32.
    "svalbard_33X": ((10.5, 78.0), 32633),
    # SW Norway: 32V is widened to 3E-12E between 56N and 64N; formula says 31.
    "norway_32V": ((4.5, 60.0), 32632),
}

SOURCES = {
    "ZONE_EXCEPTIONS": (
        "DMA TM 8358.1 (1990), Datums, Ellipsoids, Grids, and Grid Reference Systems",
        "Chapter 3, UTM grid zone exceptions: 32V widened over SW Norway (56N-64N, "
        "3E-12E); 31X/33X/35X/37X over Svalbard (72N-84N), even zones omitted",
    ),
}


def build_checks(f):
    cases = [
        ("berlin", "control", (13.4, 52.5), 32633),
        ("buenos_aires_south", "control", (-58.4, -34.6), 32721),
        *[
            (name, "edge", lonlat, code)
            for name, (lonlat, code) in ZONE_EXCEPTIONS.items()
        ],
    ]

    def make(lon, lat, exp):
        def chk():
            got = f(lon, lat)
            return int(got) == exp, f"got {got}, expected {exp}"

        return chk

    return [(name, kind, make(lon, lat, exp)) for name, kind, (lon, lat), exp in cases]
