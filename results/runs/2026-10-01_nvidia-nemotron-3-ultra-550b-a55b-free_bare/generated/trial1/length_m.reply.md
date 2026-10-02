```python
"""Module for computing geodesic length of a LineString in meters."""

from pyproj import Geod
from shapely.geometry import LineString

# WGS84 ellipsoid for geodesic calculations
_GEOD = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """
    Return the geodesic length of a LineString in meters.

    Parameters
    ----------
    line : shapely.geometry.LineString
        A LineString with coordinates in longitude/latitude (EPSG:4326).

    Returns
    -------
    float
        Length in meters. Returns 0.0 for empty or single-point lines.
    """
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0

    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        _, _, segment_length = _GEOD.inv(lon1, lat1, lon2, lat2)
        total += segment_length
    return total
```