```python
"""Buffer a WGS84 geometry by a distance in meters using a local projection."""

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    centroid = geom.centroid
    lon0, lat0 = centroid.x, centroid.y

    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +x_0=0 +y_0=0 "
        "+ellps=WGS84 +units=m +no_defs"
    )
    wgs84 = CRS.from_epsg(4326)

    to_aeqd = Transformer.from_crs(wgs84, aeqd, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(aeqd, wgs84, always_xy=True).transform

    geom_proj = transform(to_aeqd, geom)
    buffered_proj = geom_proj.buffer(distance_m)
    return transform(to_wgs84, buffered_proj)
```