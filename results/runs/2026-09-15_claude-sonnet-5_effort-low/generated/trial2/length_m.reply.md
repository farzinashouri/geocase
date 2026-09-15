```python
from shapely.geometry import LineString
from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    lons, lats = zip(*line.coords)
    _, _, distances = _GEOD.inv(
        lons[:-1], lats[:-1], lons[1:], lats[1:]
    )
    return float(sum(distances))
```