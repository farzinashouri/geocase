"""Buffer EPSG:4326 (lon/lat) shapely geometries by a distance in metres.

The geometry is projected into a local azimuthal equidistant (AEQD) projection
centred on the geometry, buffered there in metres, and projected back.
Because the projection is re-centred for every call, the result is accurate
anywhere on Earth, including high latitudes and across the antimeridian.
Buffered results that cross the antimeridian are split into parts so every
output coordinate stays within longitude [-180, 180].

Known limitation: a buffer that completely encloses a geographic pole cannot
be represented as a simple lon/lat polygon and is not special-cased here.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely import affinity, ops
from shapely.geometry import box
from shapely.geometry.base import BaseGeometry

_WGS84 = CRS.from_epsg(4326)
_METRES_PER_DEGREE = 111_320.0  # approximate, only used to pick densification steps


def _local_aeqd(lon: float, lat: float) -> CRS:
    return CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m +no_defs"
    )


def _unwrap_longitudes(geom: BaseGeometry, lon0: float) -> BaseGeometry:
    """Shift each longitude by a multiple of 360 so it lies within 180 deg of lon0.

    This removes the artificial jumps pyproj introduces when a shape straddles
    the +/-180 meridian, producing a continuous (possibly out-of-range) shape.
    """

    def _f(coords: np.ndarray) -> np.ndarray:
        out = coords.copy()
        out[:, 0] = lon0 + ((out[:, 0] - lon0 + 180.0) % 360.0) - 180.0
        return out

    return shapely.transform(geom, _f)


def _split_antimeridian(geom: BaseGeometry) -> BaseGeometry:
    """Cut a continuous lon-unwrapped geometry into [-180, 180] pieces."""
    if geom.is_empty:
        return geom
    minx, _, maxx, _ = geom.bounds
    if minx >= -180.0 and maxx <= 180.0:
        return geom
    pieces = []
    k_min = int(np.floor((minx + 180.0) / 360.0))
    k_max = int(np.floor((maxx + 180.0) / 360.0))
    for k in range(k_min, k_max + 1):
        window = box(-180.0 + 360.0 * k, -90.0, 180.0 + 360.0 * k, 90.0)
        piece = geom.intersection(window)
        if not piece.is_empty:
            pieces.append(affinity.translate(piece, xoff=-360.0 * k))
    if not pieces:
        return geom
    return ops.unary_union(pieces)


def buffer_m(geom: BaseGeometry, distance_m: float, **buffer_kwargs: Any) -> BaseGeometry:
    """Buffer an EPSG:4326 geometry by ``distance_m`` metres.

    Parameters
    ----------
    geom:
        Any shapely geometry with longitude/latitude coordinates (WGS84).
    distance_m:
        Buffer distance in metres. Negative values shrink polygons, exactly as
        with :meth:`shapely.Geometry.buffer`.
    **buffer_kwargs:
        Extra keyword arguments forwarded to shapely's ``buffer`` (for example
        ``quad_segs``, ``cap_style``, ``join_style``).

    Returns
    -------
    shapely geometry in EPSG:4326 with longitudes in [-180, 180].
    """
    if geom is None or geom.is_empty:
        return geom
    if distance_m == 0:
        return geom

    centre = geom.representative_point()
    lon0, lat0 = float(centre.x), float(centre.y)
    aeqd = _local_aeqd(lon0, lat0)
    forward = Transformer.from_crs(_WGS84, aeqd, always_xy=True)
    inverse = Transformer.from_crs(aeqd, _WGS84, always_xy=True)

    # Densify so that straight lon/lat edges and buffered arcs survive the
    # non-linear projection round trip with good fidelity.
    step_m = max(abs(float(distance_m)) / 8.0, 10.0)
    step_deg = step_m / _METRES_PER_DEGREE

    dense = shapely.segmentize(geom, step_deg)
    local = ops.transform(forward.transform, dense)
    buffered = local.buffer(float(distance_m), **buffer_kwargs)
    if buffered.is_empty:
        return buffered
    buffered = shapely.segmentize(buffered, step_m)

    back = ops.transform(inverse.transform, buffered)
    back = _unwrap_longitudes(back, lon0)
    return _split_antimeridian(back)


__all__ = ["buffer_m"]