"""Oracle for geojson_bounds (Plan 17 Phase 3).

The edge fixture is a corpus file whose polygon's longitudes jump +179 -> -179.
A naive `min/max` over the coordinates returns `(-179, 0, 179, 1)`: a bbox
spanning 358 degrees of longitude — nearly the whole planet — for a polygon two
degrees wide. No exception is raised and the tuple looks entirely plausible.
The textbook silent failure.

**The oracle is stated from first principles, not read from the corpus.** The
polygon's own coordinates bound how wide its extent can be: the two distinct
longitudes present are 179 and -179, so on a sphere the shorter arc between
them is 2 degrees and the longer is 358. A function that returns the 358-degree
complement has chosen the wrong one. Nothing here consults the case's
`case.yaml`, which is what makes this a fixture rather than an oracle — see
`benchmark/fixtures.py`.
"""

import json
import tempfile
from pathlib import Path

# Bytes only: the fixture is staged as data, exactly as the model receives it.
from geocase.benchmark.fixtures import stage_fixtures
from geocase.benchmark.registry import get_task

_CONTROL = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [13.0, 52.0],
                        [13.1, 52.0],
                        [13.1, 52.1],
                        [13.0, 52.1],
                        [13.0, 52.0],
                    ]
                ],
            },
        }
    ],
}


def build_checks(f):
    tmp = Path(tempfile.mkdtemp())
    control_path = tmp / "berlin.geojson"
    control_path.write_text(json.dumps(_CONTROL))
    staged = stage_fixtures(get_task("geojson_bounds"), tmp / "data")
    edge_path = staged["poly"]

    def control():
        got = f(str(control_path))
        try:
            lo_lon, lo_lat, hi_lon, hi_lat = (float(v) for v in got)
        except (TypeError, ValueError):
            return False, f"got {got!r}, expected a 4-tuple of floats"
        ok = (
            abs(lo_lon - 13.0) < 1e-9
            and abs(lo_lat - 52.0) < 1e-9
            and abs(hi_lon - 13.1) < 1e-9
            and abs(hi_lat - 52.1) < 1e-9
        )
        return ok, f"got {got!r}, expected (13.0, 52.0, 13.1, 52.1)"

    def antimeridian():
        got = f(str(edge_path))
        try:
            lo_lon, lo_lat, hi_lon, hi_lat = (float(v) for v in got)
        except (TypeError, ValueError):
            return False, f"got {got!r}, expected a 4-tuple of floats"
        # Latitude is unambiguous and must be right either way; getting it
        # wrong is a different bug and should not be scored as this trap.
        if not (abs(lo_lat - 0.0) < 1e-9 and abs(hi_lat - 1.0) < 1e-9):
            return False, f"got {got!r}, expected latitudes 0.0 and 1.0"
        if not (-180.0 <= lo_lon <= 180.0 and -180.0 <= hi_lon <= 180.0):
            return False, f"got {got!r}, longitudes must stay within [-180, 180]"
        # Width measured eastward from min_lon to max_lon, modulo 360. That is
        # the convention an antimeridian-crossing bbox uses: min_lon > max_lon
        # (here 179 -> -179) describes the 2-degree extent, while the naive
        # min/max result (-179 -> 179) describes its 358-degree complement.
        # Using abs() instead would score the correct answer as the wrong one.
        width = (hi_lon - lo_lon) % 360.0
        return (
            width <= 180.0,
            f"got {got!r}, spanning {width:g} deg of longitude for a polygon "
            f"2 deg wide (expected a bbox that crosses the antimeridian, not "
            f"its 358 deg complement)",
        )

    return [
        ("berlin_polygon", "control", control),
        ("antimeridian_polygon", "edge", antimeridian),
    ]
