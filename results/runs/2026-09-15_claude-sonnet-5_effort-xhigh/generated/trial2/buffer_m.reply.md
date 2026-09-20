```python
"""Buffer a WGS84 (EPSG:4326) geometry by a distance in meters."""

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

_WGS84 = CRS.from_epsg(4326)


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """Return `geom` (lon/lat, EPSG:4326) buffered by `distance_m` meters.

    Projects to a local azimuthal-equidistant CRS centered on the geometry's
    centroid (which preserves true distances from that center), buffers
    there, and reprojects back to EPSG:4326. This keeps buffering accurate
    regardless of where on Earth the geometry is located.
    """
    lon0, lat0 = geom.centroid.x, geom.centroid.y

    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )

    to_aeqd = Transformer.from_crs(_WGS84, aeqd, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(aeqd, _WGS84, always_xy=True).transform

    projected = transform(to_aeqd, geom)
    buffered = projected.buffer(distance_m)
    return transform(to_wgs84, buffered)
```