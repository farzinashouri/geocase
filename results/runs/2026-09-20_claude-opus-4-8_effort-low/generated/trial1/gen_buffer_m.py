"""Geodesically-accurate buffering of WGS84 geometries.

Buffer a shapely geometry (lon/lat, EPSG:4326) by a distance in meters and
return the result in EPSG:4326. Accuracy is achieved by projecting into a
local azimuthal-equidistant coordinate system centered on the geometry
before buffering, then projecting the result back to WGS84.

Importing this module has no side effects.
"""

from __future__ import annotations

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform

_WGS84 = CRS.from_epsg(4326)


def _aeqd_crs(lon: float, lat: float) -> CRS:
    """Azimuthal-equidistant CRS centered at (lon, lat) on a WGS84 ellipsoid.

    In this projection, distances measured from the center point are true, so
    a planar buffer around a feature near the center corresponds closely to a
    true geodesic buffer of the requested radius in meters.
    """
    return CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 "
        f"+datum=WGS84 +units=m +no_defs"
    )


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """Buffer ``geom`` (lon/lat EPSG:4326) by ``distance_m`` meters.

    Parameters
    ----------
    geom:
        A shapely geometry with coordinates as longitude/latitude in EPSG:4326.
    distance_m:
        Buffer distance in meters. May be negative to shrink the geometry.

    Returns
    -------
    BaseGeometry
        The buffered geometry, coordinates in EPSG:4326.
    """
    if geom is None or geom.is_empty:
        return geom

    # Center the local projection on the geometry so distances are accurate
    # regardless of where on Earth the feature is (including near the poles
    # and across the antimeridian for reasonably sized features).
    centroid = geom.centroid
    lon0, lat0 = centroid.x, centroid.y

    local_crs = _aeqd_crs(lon0, lat0)
    fwd = Transformer.from_crs(_WGS84, local_crs, always_xy=True)
    inv = Transformer.from_crs(local_crs, _WGS84, always_xy=True)

    local_geom = shapely_transform(fwd.transform, geom)
    buffered_local = local_geom.buffer(distance_m)
    return shapely_transform(inv.transform, buffered_local)