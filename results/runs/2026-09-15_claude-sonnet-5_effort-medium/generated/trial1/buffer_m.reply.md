```python
"""Buffer a WGS84 (EPSG:4326) geometry by a distance in meters."""

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    lon0, lat0 = geom.centroid.x, geom.centroid.y

    aeqd_crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +x_0=0 +y_0=0 "
        f"+ellps=WGS84 +units=m +no_defs"
    )
    wgs84_crs = CRS.from_epsg(4326)

    to_aeqd = Transformer.from_crs(wgs84_crs, aeqd_crs, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(aeqd_crs, wgs84_crs, always_xy=True).transform

    projected = transform(to_aeqd, geom)
    buffered = projected.buffer(distance_m)
    return transform(to_wgs84, buffered)
```