```python
from pyproj import Geod
from shapely.geometry import LineString


def length_m(line: LineString) -> float:
    """Calculate the geodesic length of a LineString in meters.
    
    Args:
        line: A shapely LineString with coordinates in EPSG:4326 (WGS84)
    
    Returns:
        The length of the line in meters
    """
    if len(line.coords) < 2:
        return 0.0
    
    geod = Geod(ellps='WGS84')
    total_length = 0.0
    coords = list(line.coords)
    
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i][:2]
        lon2, lat2 = coords[i + 1][:2]
        _, _, distance = geod.inv(lon1, lat1, lon2, lat2)
        total_length += distance
    
    return float(total_length)
```