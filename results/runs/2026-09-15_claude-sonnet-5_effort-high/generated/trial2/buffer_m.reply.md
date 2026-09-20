```python
"""Buffer a WGS84 geometry by a distance in meters, accurate anywhere on Earth."""

from functools import partial

import pyproj
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """Buffer a shapely geometry (in EPSG:4326 lon/lat) by distance_m meters.

    Projects the geometry into a local azimuthal-equidistant CRS centered on
    the geometry's centroid (which preserves distances from that center point),
    performs the buffer there, then projects the result back to EPSG:4326.
    """
    centroid = geom.centroid
    lon0, lat0 = centroid.x, centroid.y

    aeqd_crs = pyproj.CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +x_0=0 +y_0=0 "
        "+datum=WGS84 +units=m +no_defs"
    )
    wgs84_crs = pyproj.CRS.from_epsg(4326)

    to_aeqd = pyproj.Transformer.from_crs(wgs84_crs, aeqd_crs, always_xy=True).transform
    to_wgs84 = pyproj.Transformer.from_crs(aeqd_crs, wgs84_crs, always_xy=True).transform

    projected = transform(to_aeqd, geom)
    buffered = projected.buffer(distance_m)
    return transform(to_wgs84, buffered)
```