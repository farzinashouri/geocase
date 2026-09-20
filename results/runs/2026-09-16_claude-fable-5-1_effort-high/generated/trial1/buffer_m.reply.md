Here is the module: it projects into a local azimuthal equidistant projection centred on the geometry, buffers in metres, projects back, and repairs antimeridian wrap-around.

```python
"""Metre-accurate buffering of EPSG:4326 (WGS84 longitude/latitude) geometries.

The input is projected into a local azimuthal equidistant (AEQD) projection
centred on the geometry, buffered there in metres, and projected back to
longitude/latitude. Because the projection is re-centred for every call,
the result is accurate anywhere on Earth, including near the antimeridian
and at high latitudes. Output that crosses the antimeridian is split into a
MultiGeometry with all longitudes inside [-180, 180].

Known limitation: a buffer that completely surrounds a pole cannot be
represented as a simple longitude/latitude ring and is returned as-is
after the inverse projection (it will generally be invalid).
"""

from __future__ import annotations

import math

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.affinity import translate
from shapely.geometry import box
from shapely.geometry.base import BaseGeometry

_WGS84 = CRS.from_epsg(4326)


def _center_lonlat(geom: BaseGeometry) -> tuple[float, float]:
    """Spherical mean of all vertices, robust to antimeridian crossing."""
    coords = shapely.get_coordinates(geom)
    lon = np.radians(coords[:, 0])
    lat = np.radians(coords[:, 1])
    x = np.cos(lat) * np.cos(lon)
    y = np.cos(lat) * np.sin(lon)
    z = np.sin(lat)
    mx, my, mz = float(x.mean()), float(y.mean()), float(z.mean())
    if math.sqrt(mx * mx + my * my + mz * mz) < 1e-9:
        # Degenerate (e.g. antipodal vertices): fall back to the first vertex.
        return float(coords[0, 0]), float(coords[0, 1])
    lon0 = math.degrees(math.atan2(my, mx))
    lat0 = math.degrees(math.atan2(mz, math.hypot(mx, my)))
    return lon0, lat0


def _local_aeqd(lon0: float, lat0: float) -> CRS:
    return CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +datum=WGS84 +units=m +no_defs"
    )


def _split_at_antimeridian(geom: BaseGeometry) -> BaseGeometry:
    """Fold a geometry whose longitudes extend beyond [-180, 180] back into range."""
    minx, _, maxx, _ = geom.bounds
    if minx >= -180.0 and maxx <= 180.0:
        return geom
    if not geom.is_valid:
        geom = shapely.make_valid(geom)
    pieces = []
    for shift in (-360.0, 0.0, 360.0):
        window = box(-180.0 - shift, -90.0, 180.0 - shift, 90.0)
        piece = geom.intersection(window)
        if not piece.is_empty:
            pieces.append(translate(piece, xoff=shift) if shift else piece)
    if not pieces:
        return geom
    return shapely.union_all(pieces)


def buffer_m(geom: BaseGeometry, distance_m: float, **buffer_kwargs) -> BaseGeometry:
    """Buffer a WGS84 (EPSG:4326) geometry by ``distance_m`` metres.

    Parameters
    ----------
    geom:
        Any shapely geometry with longitude/latitude coordinates (EPSG:4326).
    distance_m:
        Buffer distance in metres. Positive expands, negative shrinks.
    **buffer_kwargs:
        Passed through to ``shapely.Geometry.buffer`` (e.g. ``quad_segs``,
        ``cap_style``, ``join_style``).

    Returns
    -------
    shapely geometry in EPSG:4326 with longitudes in [-180, 180].
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"geom must be a shapely geometry, got {type(geom).__name__}")
    distance_m = float(distance_m)
    if geom.is_empty:
        return geom
    if distance_m == 0.0:
        return geom.buffer(0.0, **buffer_kwargs)

    lon0, lat0 = _center_lonlat(geom)
    local = _local_aeqd(lon0, lat0)
    fwd = Transformer.from_crs(_WGS84, local, always_xy=True)
    inv = Transformer.from_crs(local, _WGS84, always_xy=True)

    def to_local(c: np.ndarray) -> np.ndarray:
        x, y = fwd.transform(c[:, 0], c[:, 1])
        return np.column_stack([x, y])

    def to_lonlat(c: np.ndarray) -> np.ndarray:
        lon, lat = inv.transform(c[:, 0], c[:, 1])
        lon = np.asarray(lon, dtype=float)
        # Unwrap longitudes relative to the projection centre so rings that
        # cross the antimeridian remain continuous (range [lon0-180, lon0+180)).
        lon = lon0 + ((lon - lon0 + 180.0) % 360.0) - 180.0
        return np.column_stack([lon, np.asarray(lat, dtype=float)])

    projected = shapely.transform(geom, to_local)
    buffered = projected.buffer(distance_m, **buffer_kwargs)
    if buffered.is_empty:
        return buffered

    result = shapely.transform(buffered, to_lonlat)
    return _split_at_antimeridian(result)


__all__ = ["buffer_m"]
```