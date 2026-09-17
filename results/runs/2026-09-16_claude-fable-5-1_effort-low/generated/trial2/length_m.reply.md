```python
"""Geodesic length of a WGS84 LineString in meters."""

from __future__ import annotations

from pyproj import Geod
from shapely.geometry import LineString

_GEOD = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the geodesic length of ``line`` (EPSG:4326 lon/lat) in meters.

    Uses the WGS84 ellipsoid via pyproj's Geod, so results are accurate
    anywhere on Earth, including across the antimeridian and near the poles.
    """
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return float(_GEOD.line_length(lons, lats))
```