"""Buffer a WGS84 (EPSG:4326) geometry by a distance in meters.

Buffering is performed in a local azimuthal equidistant projection
centered on the geometry's centroid, which preserves true distances
from that center point and so gives accurate results anywhere on
Earth (including near the poles and the antimeridian).
"""

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

_WGS84 = CRS.from_epsg(4326)


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """Return `geom` (in EPSG:4326) buffered by `distance_m` meters."""
    lon, lat = geom.centroid.x, geom.centroid.y

    local_aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )

    to_local = Transformer.from_crs(_WGS84, local_aeqd, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(local_aeqd, _WGS84, always_xy=True).transform

    projected = transform(to_local, geom)
    buffered = projected.buffer(distance_m)
    return transform(to_wgs84, buffered)