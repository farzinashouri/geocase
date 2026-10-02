```python
"""Module for calculating geodesic length of LineString geometries."""

from pyproj import Geod

def length_m(line):
    """
    Return the length of a LineString in meters, using the WGS84 ellipsoid.

    Parameters
    ----------
    line : shapely.LineString
        A LineString with coordinates in EPSG:4326 (longitude, latitude).

    Returns
    -------
    float
        Length in meters.
    """
    if line.is_empty:
        return 0.0
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0

    geod = Geod(ellps="WGS84")
    total = 0.0
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i][:2]
        lon2, lat2 = coords[i + 1][:2]
        _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
        total += dist
    return total
```