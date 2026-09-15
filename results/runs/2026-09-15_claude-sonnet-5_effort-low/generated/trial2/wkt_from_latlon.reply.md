```python
from shapely import Point


def wkt_from_latlon(lat: float, lon: float) -> str:
    return Point(lon, lat).wkt
```