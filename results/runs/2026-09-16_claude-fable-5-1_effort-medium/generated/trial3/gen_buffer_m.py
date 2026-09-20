"""Metric buffering of EPSG:4326 (lon/lat) geometries.

The geometry is projected into a local azimuthal equidistant (AEQD)
projection centred on the geometry itself, buffered in metres there, and
projected back to WGS84. Because the projection is re-centred for every
call, distances are true near the geometry regardless of latitude, and the
approach works at the poles and across the antimeridian (where a naive
"mean longitude" centre would be wrong).
"""

from __future__ import annotations

import math

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry

__all__ = ["buffer_m"]

_WGS84 = CRS.from_epsg(4326)


def _center_lonlat(geom: BaseGeometry) -> tuple[float, float]:
    """Return a lon/lat centre for ``geom`` computed on the unit sphere.

    Averaging 3-D unit vectors (instead of raw longitudes) gives a sensible
    centre for geometries that straddle the antimeridian or sit at a pole.
    """
    coords = shapely.get_coordinates(geom)
    lon = np.radians(coords[:, 0])
    lat = np.radians(coords[:, 1])
    cos_lat = np.cos(lat)
    x = float(np.mean(cos_lat * np.cos(lon)))
    y = float(np.mean(cos_lat * np.sin(lon)))
    z = float(np.mean(np.sin(lat)))
    norm = math.sqrt(x * x + y * y + z * z)
    if norm < 1e-9:
        # Points are spread (near-)antipodally; any centre is as good as
        # another, so use the first vertex.
        return float(coords[0, 0]), float(coords[0, 1])
    return (
        math.degrees(math.atan2(y, x)),
        math.degrees(math.asin(max(-1.0, min(1.0, z / norm)))),
    )


def _local_aeqd(lon_0: float, lat_0: float) -> CRS:
    return CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat_0:.10f} +lon_0={lon_0:.10f} "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )


def buffer_m(geom: BaseGeometry, distance_m: float, **buffer_kwargs) -> BaseGeometry:
    """Buffer a lon/lat (EPSG:4326) geometry by ``distance_m`` metres.

    Parameters
    ----------
    geom:
        Any shapely geometry with coordinates in longitude/latitude degrees
        on WGS84 (x = lon, y = lat).
    distance_m:
        Buffer distance in metres. Negative values shrink polygons, as with
        ``shapely.buffer``.
    **buffer_kwargs:
        Passed through to ``shapely.buffer`` (e.g. ``quad_segs``,
        ``cap_style``, ``join_style``).

    Returns
    -------
    BaseGeometry
        The buffered geometry, with coordinates back in EPSG:4326.
        Longitudes are normalised to [-180, 180]; a result that crosses
        the antimeridian is therefore returned with a longitude jump rather
        than being split into two parts.
    """
    if geom is None or geom.is_empty:
        return geom

    lon_0, lat_0 = _center_lonlat(geom)
    local = _local_aeqd(lon_0, lat_0)

    fwd = Transformer.from_crs(_WGS84, local, always_xy=True)
    inv = Transformer.from_crs(local, _WGS84, always_xy=True)

    def _to_local(pts: np.ndarray) -> np.ndarray:
        x, y = fwd.transform(pts[:, 0], pts[:, 1])
        return np.column_stack([x, y])

    def _to_wgs84(pts: np.ndarray) -> np.ndarray:
        lon, lat = inv.transform(pts[:, 0], pts[:, 1])
        return np.column_stack([lon, lat])

    projected = shapely.transform(geom, _to_local)
    buffered = shapely.buffer(projected, float(distance_m), **buffer_kwargs)
    return shapely.transform(buffered, _to_wgs84)