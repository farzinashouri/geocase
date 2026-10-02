```python
from shapely.geometry import LineString
from pyproj import Geod

# WGS84 ellipsoid for geodesic calculations
_GEOD = Geod(ellps="WGS84")

def length_m(line: LineString) -> float:
    """Return the geodesic length of a LineString in meters.

    The LineString must be in EPSG:4326 (longitude, latitude).
    """
    if line.is_empty:
        return 0.0
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0
    lons, lats = zip(*coords)
    # pyproj.Geod.line_length returns length in meters
    return _GEOD.line_length(lons, lats)
```