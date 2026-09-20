```python
"""Buffer EPSG:4326 (lon/lat) geometries by a distance expressed in meters.

The approach: for each single-part geometry, build an azimuthal equidistant
projection centred on a point lying on that geometry, project into it, buffer
in metres, and project back.  Because the projection is local to the
geometry, distortion is negligible for real-world buffer sizes anywhere on
Earth, including near the poles and across the antimeridian.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry

__all__ = ["buffer_m"]

_WGS84 = CRS.from_epsg(4326)


@lru_cache(maxsize=512)
def _transformers(lon_0: float, lat_0: float) -> tuple[Transformer, Transformer]:
    """Forward/inverse transformers for a local AEQD projection centred at (lon_0, lat_0)."""
    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat_0} +lon_0={lon_0} +x_0=0 +y_0=0 "
        "+datum=WGS84 +units=m +no_defs"
    )
    forward = Transformer.from_crs(_WGS84, aeqd, always_xy=True)
    inverse = Transformer.from_crs(aeqd, _WGS84, always_xy=True)
    return forward, inverse


def _projection_center(geom: BaseGeometry) -> tuple[float, float]:
    """A point on the geometry, rounded so nearby geometries share a cached projection."""
    pt = geom.representative_point()
    return round(pt.x, 3), round(pt.y, 3)


def _buffer_single(geom: BaseGeometry, distance_m: float, kwargs: dict[str, Any]) -> BaseGeometry:
    lon_0, lat_0 = _projection_center(geom)
    forward, inverse = _transformers(lon_0, lat_0)

    def to_local(coords: np.ndarray) -> np.ndarray:
        x, y = forward.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([x, y])

    def to_lonlat(coords: np.ndarray) -> np.ndarray:
        lon, lat = inverse.transform(coords[:, 0], coords[:, 1])
        lon = np.asarray(lon, dtype=float)
        lat = np.asarray(lat, dtype=float)
        # Unwrap longitudes so a ring straddling the antimeridian stays
        # continuous (values may fall slightly outside [-180, 180]).
        lon = lon_0 + ((lon - lon_0 + 180.0) % 360.0) - 180.0
        return np.column_stack([lon, lat])

    local = shapely.transform(geom, to_local)
    buffered = local.buffer(distance_m, **kwargs)
    if buffered.is_empty:
        return buffered
    return shapely.transform(buffered, to_lonlat)


def buffer_m(geom: BaseGeometry, distance_m: float, **buffer_kwargs: Any) -> BaseGeometry:
    """Buffer a lon/lat (EPSG:4326) geometry by ``distance_m`` metres.

    Parameters
    ----------
    geom
        Any shapely geometry with coordinates in EPSG:4326 (x=longitude,
        y=latitude).  Multi-part geometries and collections are supported;
        each part is buffered in its own local projection and the results
        are unioned.
    distance_m
        Buffer distance in metres.  Negative values shrink polygons.
    **buffer_kwargs
        Extra keyword arguments forwarded to ``shapely`` ``buffer`` (e.g.
        ``quad_segs``, ``cap_style``, ``join_style``).

    Returns
    -------
    shapely geometry
        The buffered geometry in EPSG:4326.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"geom must be a shapely geometry, got {type(geom).__name__}")
    distance_m = float(distance_m)
    if not math.isfinite(distance_m):
        raise ValueError("distance_m must be a finite number")

    if geom.is_empty:
        return shapely.Polygon()

    if hasattr(geom, "geoms"):  # Multi* or GeometryCollection
        parts = [buffer_m(part, distance_m, **buffer_kwargs) for part in geom.geoms]
        parts = [p for p in parts if not p.is_empty]
        if not parts:
            return shapely.Polygon()
        if len(parts) == 1:
            return parts[0]
        return shapely.union_all(parts)

    return _buffer_single(geom, distance_m, buffer_kwargs)
```