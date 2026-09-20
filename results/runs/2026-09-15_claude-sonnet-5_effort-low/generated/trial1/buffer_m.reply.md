```python
"""Buffer a WGS84 geometry by a distance in meters using a local azimuthal projection."""

from shapely.geometry import shape, mapping
from shapely.ops import transform
import pyproj


def buffer_m(geom, distance_m):
    lon, lat = geom.centroid.x, geom.centroid.y

    aeqd_crs = pyproj.CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m +no_defs"
    )
    wgs84_crs = pyproj.CRS.from_epsg(4326)

    to_aeqd = pyproj.Transformer.from_crs(wgs84_crs, aeqd_crs, always_xy=True).transform
    to_wgs84 = pyproj.Transformer.from_crs(aeqd_crs, wgs84_crs, always_xy=True).transform

    projected = transform(to_aeqd, geom)
    buffered = projected.buffer(distance_m)
    result = transform(to_wgs84, buffered)

    return result
```