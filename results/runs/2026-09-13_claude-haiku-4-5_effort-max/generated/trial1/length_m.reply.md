```python
from pyproj import Geodesic
from shapely.geometry import LineString

def length_m(line: LineString) -> float:
    geod = Geodesic.from_ellps("WGS84")
    coords = list(line.coords)
    total_length = 0.0
    
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        result = geod.inverse(lon1, lat1, lon2, lat2)
        total_length += result['s12']
    
    return total_length
```