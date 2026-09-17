"""Buffer WGS84 (EPSG:4326) geometries by a distance in meters.

The geometry is projected to a local Azimuthal Equidistant projection centred on
its centroid, buffered there in meters, and projected back. This is accurate for
any location on Earth, including polar regions and geometries near the
antimeridian, as long as the geometry's extent is small relative to the globe
(which is the case for typical buffering tasks).
"""

from __future__ import annotations

import math

import numpy as np
from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

_WGS84 = CRS.from_epsg(4326)


def _centre_of(geom: BaseGeometry) -> tuple[float, float]:
    """Return a (lon, lat) centre robust to antimeridian-crossing geometries.

    Uses the mean of unit vectors on the sphere so a geometry straddling
    +/-180 degrees does not get a bogus centroid near longitude 0.
    """
    coords = np.asarray(
        [c for c in _iter_coords(geom)], dtype=float
    )
    lon = np.radians(coords[:, 0])
    lat = np.radians(coords[:, 1])
    x = np.mean(np.cos(lat) * np.cos(lon))
    y = np.mean(np.cos(lat) * np.sin(lon))
    z = np.mean(np.sin(lat))
    norm = math.hypot(x, y)
    if norm == 0.0 and z == 0.0:
        # Degenerate (points evenly spread around the globe); fall back.
        c = geom.centroid
        return float(c.x), float(c.y)
    return math.degrees(math.atan2(y, x)), math.degrees(math.atan2(z, norm))


def _iter_coords(geom: BaseGeometry):
    if geom.is_empty:
        return
    gtype = geom.geom_type
    if gtype == "Point":
        yield geom.coords[0]
    elif gtype in ("LineString", "LinearRing"):
        yield from geom.coords
    elif gtype == "Polygon":
        yield from geom.exterior.coords
        for ring in geom.interiors:
            yield from ring.coords
    else:  # Multi* and GeometryCollection
        for part in geom.geoms:
            yield from _iter_coords(part)


def buffer_m(geom: BaseGeometry, distance_m: float, **buffer_kwargs) -> BaseGeometry:
    """Buffer ``geom`` (lon/lat, EPSG:4326) by ``distance_m`` meters.

    Parameters
    ----------
    geom:
        Any shapely geometry with coordinates in EPSG:4326 (x=longitude,
        y=latitude, degrees).
    distance_m:
        Buffer distance in meters. Negative values shrink polygons.
    **buffer_kwargs:
        Extra keyword arguments forwarded to ``shapely.buffer`` (for example
        ``quad_segs``, ``cap_style``, ``join_style``).

    Returns
    -------
    shapely geometry
        The buffered geometry, with coordinates in EPSG:4326.
    """
    if geom is None or geom.is_empty:
        return geom

    lon0, lat0 = _centre_of(geom)

    local_crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )

    to_local = Transformer.from_crs(_WGS84, local_crs, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(local_crs, _WGS84, always_xy=True).transform

    projected = transform(to_local, geom)
    buffered = projected.buffer(distance_m, **buffer_kwargs)
    return transform(to_wgs84, buffered)


__all__ = ["buffer_m"]