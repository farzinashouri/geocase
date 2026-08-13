"""Buffer a WGS84 (EPSG:4326) geometry by a distance in meters.

The geometry is projected into a local azimuthal equidistant (AEQD)
projection centered on the geometry, buffered in that planar meter-based
space, and projected back to EPSG:4326. Because the AEQD projection is
re-centered on each input geometry, the result is accurate anywhere on
Earth, including near the poles.
"""

from pyproj import CRS, Transformer
from shapely.ops import transform as _shapely_transform

_WGS84 = CRS.from_epsg(4326)


def buffer_m(geom, distance_m):
    """Buffer *geom* (shapely geometry, lon/lat EPSG:4326) by *distance_m* meters.

    Returns a shapely geometry with lon/lat EPSG:4326 coordinates.
    """
    if geom.is_empty:
        return geom

    # Center a local azimuthal equidistant projection on the geometry so
    # planar distances near the geometry closely match geodesic meters.
    centroid = geom.centroid
    lon0, lat0 = centroid.x, centroid.y
    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +x_0=0 +y_0=0 "
        "+datum=WGS84 +units=m +no_defs"
    )

    to_aeqd = Transformer.from_crs(_WGS84, aeqd, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(aeqd, _WGS84, always_xy=True).transform

    projected = _shapely_transform(to_aeqd, geom)
    buffered = projected.buffer(distance_m)
    return _shapely_transform(to_wgs84, buffered)
