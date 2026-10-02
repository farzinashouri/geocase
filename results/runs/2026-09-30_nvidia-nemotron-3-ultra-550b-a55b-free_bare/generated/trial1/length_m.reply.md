```python
from shapely.geometry import LineString
from pyproj import Geod

# WGS84 ellipsoid geodetic calculator
_GEOD = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the geodesic length of a LineString in meters.

    The LineString must use EPSG:4326 coordinates (longitude, latitude).
    Returns 0.0 for empty or single-point lines.
    """
    if line.is_empty:
        return 0.0

    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0

    lons, lats = zip(*coords)
    return _GEOD.line_length(lons, lats)
```