"""Geodesic-aware buffering of EPSG:4326 (WGS84) shapely geometries.

The input geometry is projected to a local azimuthal equidistant projection
centred on the geometry's own centroid, buffered there in metres, and
projected back to longitude/latitude. Distances measured from the projection
centre are exact in this projection, so results remain accurate at any
latitude, including the poles, and are not affected by the antimeridian
because the projection is centred on the geometry itself.
"""

from __future__ import annotations

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

_WGS84 = CRS.from_epsg(4326)


def _local_aeqd(lon: float, lat: float) -> CRS:
    """Return an azimuthal equidistant CRS centred at (lon, lat) on WGS84."""
    return CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 "
        "+datum=WGS84 +units=m +no_defs"
    )


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """Buffer a lon/lat (EPSG:4326) geometry by ``distance_m`` metres.

    Parameters
    ----------
    geom:
        Any shapely geometry with coordinates in EPSG:4326 (x=longitude,
        y=latitude, degrees).
    distance_m:
        Buffer distance in metres. Positive expands the geometry; negative
        shrinks polygons, as with ``shapely`` buffering.

    Returns
    -------
    shapely geometry with coordinates in EPSG:4326.
    """
    if geom is None or geom.is_empty:
        return geom

    centroid = geom.centroid
    if centroid.is_empty:
        # Degenerate case (should not normally happen for non-empty input).
        pt = geom.representative_point()
        lon0, lat0 = pt.x, pt.y
    else:
        lon0, lat0 = centroid.x, centroid.y

    local_crs = _local_aeqd(lon0, lat0)
    to_local = Transformer.from_crs(_WGS84, local_crs, always_xy=True)
    to_wgs84 = Transformer.from_crs(local_crs, _WGS84, always_xy=True)

    projected = transform(to_local.transform, geom)
    buffered = projected.buffer(distance_m)
    return transform(to_wgs84.transform, buffered)


__all__ = ["buffer_m"]