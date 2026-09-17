```python
"""Project a WGS84 LineString into a projected CRS along geodesic paths.

The output line follows the geodesic between every pair of consecutive
input vertices to within 25 km. Segments are densified on the ellipsoid
with pyproj's Geod before being transformed, so the straight chords of the
returned line stay close to the true geodesic in the target CRS.
"""

from __future__ import annotations

import math

from pyproj import Geod, Transformer
from shapely.geometry import LineString

# Maximum geodesic spacing between emitted vertices, in metres. A chord of
# this length departs from the great-circle arc by roughly L^2 / (8R), which
# is about 0.2 km on Earth: far inside the 25 km tolerance and enough slack
# to absorb projection distortion of the straight segments.
_MAX_SPACING_M = 100_000.0

_WGS84 = Geod(ellps="WGS84")


def _densify_segment(lon1, lat1, lon2, lat2):
    """Yield (lon, lat) pairs from the first point up to but excluding the last."""
    yield (lon1, lat1)
    _, _, dist = _WGS84.inv(lon1, lat1, lon2, lat2)
    if dist <= _MAX_SPACING_M:
        return
    n_segments = math.ceil(dist / _MAX_SPACING_M)
    for lon, lat in _WGS84.npts(lon1, lat1, lon2, lat2, n_segments - 1):
        yield (lon, lat)


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Return `line` projected into EPSG:`dst_epsg`, following geodesics.

    `line` must have longitude/latitude coordinates in EPSG:4326. The result
    traces the geodesic between each pair of consecutive vertices to within
    25 km, adding intermediate vertices where needed.
    """
    coords = [(float(x), float(y)) for x, y, *_ in line.coords]
    if len(coords) < 2:
        raise ValueError("project_line requires a LineString with at least two vertices")

    lonlats = []
    for (lon1, lat1), (lon2, lat2) in zip(coords[:-1], coords[1:]):
        lonlats.extend(_densify_segment(lon1, lat1, lon2, lat2))
    lonlats.append(coords[-1])

    transformer = Transformer.from_crs(4326, int(dst_epsg), always_xy=True)
    lons = [p[0] for p in lonlats]
    lats = [p[1] for p in lonlats]
    xs, ys = transformer.transform(lons, lats)
    return LineString(list(zip(xs, ys)))
```