```python
"""Buffer geometries with EPSG:4326 coordinates by a distance in meters."""

from pyproj import Transformer
from shapely.geometry import Point
from shapely.ops import transform


def buffer_m(geom, distance_m):
    """Buffer a WGS84 (EPSG:4326) geometry by a distance in meters.

    Uses an azimuthal equidistant projection centered on the geometry's
    centroid, which preserves distances from that center point exactly,
    so the buffer distance is accurate regardless of where on Earth the
    geometry is located (poles, antimeridian, equator, etc.).
    """
    centroid = geom.centroid
    lon_0, lat_0 = centroid.x, centroid.y

    aeqd_crs = (
        f"+proj=aeqd +lat_0={lat_0} +lon_0={lon_0} "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )

    to_aeqd = Transformer.from_crs("EPSG:4326", aeqd_crs, always_xy=True)
    to_wgs84 = Transformer.from_crs(aeqd_crs, "EPSG:4326", always_xy=True)

    projected = transform(to_aeqd.transform, geom)
    buffered = projected.buffer(distance_m)
    result = transform(to_wgs84.transform, buffered)

    return result
```