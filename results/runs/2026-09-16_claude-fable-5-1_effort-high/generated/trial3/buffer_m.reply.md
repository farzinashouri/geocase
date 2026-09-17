```python
"""Geodesic-aware buffering of EPSG:4326 (WGS84 longitude/latitude) geometries.

``buffer_m(geom, distance_m)`` buffers a shapely geometry whose coordinates are
lon/lat degrees by a distance expressed in metres and returns lon/lat again.

How it works
------------
Each elementary part of the input (point, line or polygon) is projected into
its own local azimuthal-equidistant projection (AEQD) on the WGS84 ellipsoid,
centred on that part.  The planar buffer is computed there, the result is
densified so that its shape survives the trip back, and it is re-projected to
lon/lat.  The parts are then unioned.

Because AEQD preserves distance and direction from its centre exactly, a
buffered point is an exact geodesic circle at any latitude (including the
poles), and buffers of lines and polygons are accurate to a small fraction of a
percent for parts up to a few thousand kilometres across.

Limitations
-----------
The output is ordinary planar lon/lat in [-180, 180] x [-90, 90].  A result
that crosses the antimeridian or encloses a pole cannot be represented as a
simple polygon in those coordinates without splitting; this module does not
perform that split.  Z values on the input are dropped.
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Iterator

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry

__all__ = ["buffer_m"]

_LEAF_TYPES = ("Point", "LineString", "LinearRing", "Polygon")


@lru_cache(maxsize=1)
def _wgs84() -> CRS:
    return CRS.from_epsg(4326)


def _local_aeqd(lon0: float, lat0: float) -> CRS:
    return CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0:.10f} +lon_0={lon0:.10f} "
        "+datum=WGS84 +units=m +no_defs +type=crs"
    )


def _leaf_parts(geom: BaseGeometry) -> Iterator[BaseGeometry]:
    """Yield the non-empty single-part geometries inside ``geom`` (any nesting)."""
    if geom.is_empty:
        return
    if geom.geom_type in _LEAF_TYPES:
        yield geom
        return
    for part in geom.geoms:
        yield from _leaf_parts(part)


def _center(geom: BaseGeometry) -> tuple[float, float]:
    """Spherical mean of the vertices (robust across the antimeridian and poles)."""
    coords = shapely.get_coordinates(geom)
    lon = np.radians(coords[:, 0])
    lat = np.radians(coords[:, 1])
    cos_lat = np.cos(lat)
    x = float(np.mean(cos_lat * np.cos(lon)))
    y = float(np.mean(cos_lat * np.sin(lon)))
    z = float(np.mean(np.sin(lat)))
    if math.hypot(x, y, z) < 1e-12:  # degenerate (vertices antipodally balanced)
        return float(coords[0, 0]), float(coords[0, 1])
    lon0 = math.degrees(math.atan2(y, x))
    lat0 = math.degrees(math.atan2(z, math.hypot(x, y)))
    return lon0, lat0


def _apply(geom: BaseGeometry, transformer: Transformer) -> BaseGeometry:
    def _fn(xy: np.ndarray) -> np.ndarray:
        x, y = transformer.transform(xy[:, 0], xy[:, 1])
        return np.column_stack((x, y))

    return shapely.transform(geom, _fn)


def _buffer_part(part: BaseGeometry, distance_m: float, **buffer_kwargs) -> BaseGeometry:
    lon0, lat0 = _center(part)
    local = _local_aeqd(lon0, lat0)
    fwd = Transformer.from_crs(_wgs84(), local, always_xy=True)
    inv = Transformer.from_crs(local, _wgs84(), always_xy=True)

    projected = _apply(part, fwd)
    buffered = projected.buffer(distance_m, **buffer_kwargs)
    if buffered.is_empty:
        return buffered

    # Densify in the projected plane so long straight edges keep their shape
    # once unprojected. The floor on segment length bounds the vertex count.
    minx, miny, maxx, maxy = buffered.bounds
    diag = math.hypot(maxx - minx, maxy - miny)
    max_seg = max(abs(distance_m) / 4.0, diag / 256.0)
    if max_seg > 0.0:
        buffered = shapely.segmentize(buffered, max_seg)

    return _apply(buffered, inv)


def buffer_m(
    geom: BaseGeometry,
    distance_m: float,
    *,
    quad_segs: int = 16,
    cap_style: str = "round",
    join_style: str = "round",
    mitre_limit: float = 5.0,
) -> BaseGeometry:
    """Buffer an EPSG:4326 geometry by ``distance_m`` metres.

    Parameters
    ----------
    geom
        Any shapely geometry with longitude/latitude coordinates (WGS84).
    distance_m
        Buffer distance in metres. Negative values shrink polygons.
    quad_segs, cap_style, join_style, mitre_limit
        Passed through to :meth:`shapely.Geometry.buffer`.

    Returns
    -------
    shapely geometry in EPSG:4326 (lon/lat). Empty input, or a negative buffer
    that consumes the geometry, yields an empty polygon.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"geom must be a shapely geometry, got {type(geom).__name__}")
    distance_m = float(distance_m)
    if not math.isfinite(distance_m):
        raise ValueError("distance_m must be a finite number")

    geom = shapely.force_2d(geom)
    if geom.is_empty:
        return shapely.Polygon()

    kwargs = dict(
        quad_segs=quad_segs,
        cap_style=cap_style,
        join_style=join_style,
        mitre_limit=mitre_limit,
    )
    results = [
        r
        for r in (_buffer_part(p, distance_m, **kwargs) for p in _leaf_parts(geom))
        if not r.is_empty
    ]
    if not results:
        return shapely.Polygon()
    if len(results) == 1:
        return results[0]
    return shapely.union_all(results)
```