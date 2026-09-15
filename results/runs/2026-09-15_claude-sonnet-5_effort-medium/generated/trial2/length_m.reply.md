```python
from pyproj import Geod
from shapely.geometry import LineString

_GEOD = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    lons = [c[0] for c in line.coords]
    lats = [c[1] for c in line.coords]
    _, _, distance = _GEOD.inv(lons[:-1], lats[:-1], lons[1:], lats[1:])
    return float(sum(distance))
```