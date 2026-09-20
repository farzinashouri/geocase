```python
from shapely.geometry import Point

def wkt_from_latlon(lat, lon):
    point = Point(lon, lat)
    return point.wkt
```