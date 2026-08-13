"""Buffer a WGS84 (EPSG:4326) geometry by a distance in meters.

The geometry is projected into a local azimuthal equidistant (AEQD)
projection centered on the geometry itself, buffered in that planar
metric space, and projected back to EPSG:4326. Because the AEQD
projection is centered on the geometry, distances from the center are
true, giving accurate buffers anywhere on Earth (including near the
poles), for geometries of local/regional extent.
"""

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

__all__ = ["buffer_m"]

_WGS84 = CRS.from_epsg(4326)


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """Return *geom* buffered by *distance_m* meters.

    Parameters
    ----------
    geom : shapely geometry
        Geometry with longitude/latitude coordinates in EPSG:4326.
    distance_m : float
        Buffer distance in meters (positive expands the geometry).

    Returns
    -------
    shapely geometry
        The buffered geometry, with coordinates in EPSG:4326.
    """
    if geom.is_empty:
        return geom

    # Center the local projection on a point guaranteed to represent the
    # geometry (centroid works for all geometry types).
    center = geom.centroid
    lon_0, lat_0 = center.x, center.y

    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat_0} +lon_0={lon_0} "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )

    to_aeqd = Transformer.from_crs(_WGS84, aeqd, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(aeqd, _WGS84, always_xy=True).transform

    projected = transform(to_aeqd, geom)
    buffered = projected.buffer(distance_m)
    return transform(to_wgs84, buffered)
