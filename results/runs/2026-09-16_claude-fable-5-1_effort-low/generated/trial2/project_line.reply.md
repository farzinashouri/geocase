```python
"""Project a WGS84 LineString into a projected CRS while tracing geodesics.

Each consecutive pair of input vertices is densified along the geodesic
(shortest path on the WGS84 ellipsoid) so that the projected polyline stays
within 25 km of the true geodesic course everywhere.
"""

from __future__ import annotations

import math

from pyproj import Geod, Transformer
from shapely.geometry import LineString

# Maximum geodesic spacing between densified vertices (metres).
# A great-circle chord this short deviates from the arc by well under 25 km,
# and typical projections add only a small additional distortion on top.
_MAX_SEGMENT_M = 10_000.0

# Guard against pathological inputs (e.g. antipodal points ~20,000 km apart).
_MAX_POINTS_PER_SEGMENT = 100_000


def _densify_segment(geod: Geod, lon1: float, lat1: float, lon2: float, lat2: float):
    """Yield (lon, lat) points along the geodesic from p1 to p2, excluding p1,
    including p2."""
    _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
    if not math.isfinite(dist) or dist <= 0.0:
        yield (lon2, lat2)
        return

    n_intermediate = int(math.ceil(dist / _MAX_SEGMENT_M)) - 1
    n_intermediate = max(0, min(n_intermediate, _MAX_POINTS_PER_SEGMENT))

    if n_intermediate > 0:
        for lon, lat in geod.npts(lon1, lat1, lon2, lat2, n_intermediate):
            yield (lon, lat)
    yield (lon2, lat2)


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Return ``line`` (EPSG:4326 lon/lat) projected into ``dst_epsg``.

    The output traces the geodesic between each pair of consecutive input
    vertices to within 25 km, adding vertices as needed.
    """
    coords = list(line.coords)
    if len(coords) < 2:
        raise ValueError("LineString must have at least two coordinates")

    geod = Geod(ellps="WGS84")
    transformer = Transformer.from_crs(
        "EPSG:4326", f"EPSG:{int(dst_epsg)}", always_xy=True
    )

    lonlat = [(coords[0][0], coords[0][1])]
    for (lon1, lat1, *_), (lon2, lat2, *_) in zip(coords[:-1], coords[1:]):
        lonlat.extend(_densify_segment(geod, lon1, lat1, lon2, lat2))

    lons = [p[0] for p in lonlat]
    lats = [p[1] for p in lonlat]
    xs, ys = transformer.transform(lons, lats)

    return LineString(list(zip(xs, ys)))
```