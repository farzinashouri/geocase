```python
from pyproj import Geod
from shapely.geometry import LineString


def length_m(line: LineString) -> float:
    """Return the geodesic length in meters of a WGS84 lon/lat LineString."""
    geod = Geod(ellps="WGS84")
    lons, lats = line.xy
    return float(geod.line_length(lons, lats))
```