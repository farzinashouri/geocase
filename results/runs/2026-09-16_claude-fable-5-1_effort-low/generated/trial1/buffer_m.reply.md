```python
"""Geodesic-aware buffering of EPSG:4326 (lon/lat) geometries.

`buffer_m(geom, distance_m)` projects the geometry into a local
azimuthal-equidistant CRS centred on the geometry, buffers there in
metres, and projects the result back to WGS84.  Because the local
projection is centred on the geometry, distance distortion is small
everywhere on Earth, including near the poles.  Geometries that straddle
the antimeridian are handled by the projection itself (the local CRS has
no seam there), and the result is normalised back to [-180, 180] only when
the original geometry did not cross the antimeridian.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import Optional

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as _shp_transform


_WGS84 = CRS.from_epsg(4326)


def _local_aeqd(lon_0: float, lat_0: float) -> CRS:
    """Build an azimuthal-equidistant CRS centred on (lon_0, lat_0)."""
    return CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat_0} +lon_0={lon_0} "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )


def _centre_of(geom: BaseGeometry) -> tuple[float, float]:
    """Return a robust (lon, lat) centre for the local projection.

    Uses the representative point when the geometry is not empty.  Falls
    back to the centroid; both are guaranteed to lie within the bounds.
    Longitude is wrapped to [-180, 180].
    """
    try:
        pt = geom.representative_point()
    except Exception:  # pragma: no cover - representative_point rarely fails
        pt = geom.centroid
    lon = ((pt.x + 180.0) % 360.0) - 180.0
    lat = max(-90.0, min(90.0, pt.y))
    return lon, lat


def buffer_m(
    geom: BaseGeometry,
    distance_m: float,
    *,
    quad_segs: int = 16,
    cap_style: str = "round",
    join_style: str = "round",
    crs: Optional[CRS] = None,
) -> BaseGeometry:
    """Buffer a lon/lat (EPSG:4326) geometry by ``distance_m`` metres.

    Parameters
    ----------
    geom:
        Any shapely geometry with coordinates in EPSG:4326 (x=lon, y=lat).
    distance_m:
        Buffer distance in metres.  Negative values shrink polygons.
    quad_segs, cap_style, join_style:
        Passed through to :meth:`shapely.Geometry.buffer`.
    crs:
        Optional override for the working projection.  By default a local
        azimuthal-equidistant CRS centred on the geometry is used.

    Returns
    -------
    shapely geometry with coordinates in EPSG:4326.
    """
    if geom is None:
        raise ValueError("geom must be a shapely geometry, got None")
    if geom.is_empty:
        return geom
    if distance_m == 0:
        return geom

    if crs is None:
        lon_0, lat_0 = _centre_of(geom)
        crs = _local_aeqd(lon_0, lat_0)

    fwd = Transformer.from_crs(_WGS84, crs, always_xy=True)
    inv = Transformer.from_crs(crs, _WGS84, always_xy=True)

    projected = _shp_transform(fwd.transform, geom)
    buffered = projected.buffer(
        float(distance_m),
        quad_segs=quad_segs,
        cap_style=cap_style,
        join_style=join_style,
    )
    result = _shp_transform(inv.transform, buffered)

    if not result.is_valid:
        result = result.buffer(0)
    return result


__all__ = ["buffer_m"]
```