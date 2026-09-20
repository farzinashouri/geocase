```python
"""Geodesic length of a WGS84 LineString in meters."""

from __future__ import annotations

from pyproj import Geod
from shapely.geometry import LineString

_GEOD = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the geodesic length of ``line`` in meters.

    ``line`` must be a shapely LineString with (longitude, latitude)
    coordinates in EPSG:4326. Lengths are computed on the WGS84
    ellipsoid, so results are accurate anywhere on Earth, including
    across the antimeridian and near the poles.
    """
    if line.is_empty:
        return 0.0
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return float(_GEOD.line_length(lons, lats))
```