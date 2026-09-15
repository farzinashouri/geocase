"""Buffer a geometry with EPSG:4326 (lon/lat) coordinates by a distance in meters.

Projects the geometry into a local azimuthal-equidistant projection centered
on its centroid (so distances measured from that point are accurate anywhere
on Earth, including near the poles and across the antimeridian), performs the
buffer in that metric CRS, and reprojects the result back to EPSG:4326.
"""

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

_WGS84 = CRS.from_epsg(4326)


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """Return `geom` (lon/lat, EPSG:4326) buffered by `distance_m` meters."""
    lon, lat = geom.centroid.x, geom.centroid.y

    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )

    to_aeqd = Transformer.from_crs(_WGS84, aeqd, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(aeqd, _WGS84, always_xy=True).transform

    projected = transform(to_aeqd, geom)
    buffered = projected.buffer(distance_m)
    return transform(to_wgs84, buffered)