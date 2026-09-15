```python
from shapely.geometry import Point


def wkt_from_latlon(lat, lon):
    return Point(lon, lat).wkt
```