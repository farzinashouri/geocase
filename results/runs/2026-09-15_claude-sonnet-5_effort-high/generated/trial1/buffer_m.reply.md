```python
"""Buffer a WGS84 geometry by a distance in meters, accurately anywhere on Earth."""

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """Buffer a shapely geometry (lon/lat, EPSG:4326) by distance_m meters.

    The geometry is reprojected into a local azimuthal-equidistant
    projection centered on its centroid (which preserves distances from
    that center point), buffered there, and reprojected back to EPSG:4326.
    """
    centroid = geom.centroid
    lon0, lat0 = centroid.x, centroid.y

    aeqd_crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +x_0=0 +y_0=0 "
        "+ellps=WGS84 +units=m +no_defs"
    )
    wgs84_crs = CRS.from_epsg(4326)

    to_aeqd = Transformer.from_crs(wgs84_crs, aeqd_crs, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(aeqd_crs, wgs84_crs, always_xy=True).transform

    geom_local = transform(to_aeqd, geom)
    buffered_local = geom_local.buffer(distance_m)
    buffered_wgs84 = transform(to_wgs84, buffered_local)

    return buffered_wgs84
```