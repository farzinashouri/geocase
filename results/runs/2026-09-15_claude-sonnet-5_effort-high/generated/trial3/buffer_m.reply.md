```python
"""Buffer a WGS84 geometry by a distance in meters using a local equidistant projection."""

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """Buffer a shapely geometry (lon/lat, EPSG:4326) by `distance_m` meters.

    Uses a local azimuthal equidistant projection centered on the geometry's
    centroid so that distances are accurate regardless of location on Earth,
    then buffers in that projection and reprojects back to EPSG:4326.
    """
    centroid = geom.centroid
    lon_0, lat_0 = centroid.x, centroid.y

    wgs84 = CRS.from_epsg(4326)
    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat_0} +lon_0={lon_0} +x_0=0 +y_0=0 "
        f"+ellps=WGS84 +units=m +no_defs"
    )

    to_aeqd = Transformer.from_crs(wgs84, aeqd, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(aeqd, wgs84, always_xy=True).transform

    geom_aeqd = transform(to_aeqd, geom)
    buffered_aeqd = geom_aeqd.buffer(distance_m)
    buffered_wgs84 = transform(to_wgs84, buffered_aeqd)

    return buffered_wgs84
```