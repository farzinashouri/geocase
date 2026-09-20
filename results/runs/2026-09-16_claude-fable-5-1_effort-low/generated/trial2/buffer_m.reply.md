```python
"""Geodesically accurate buffering of EPSG:4326 geometries.

The geometry is projected to a local azimuthal equidistant projection
centered on its centroid, buffered in meters there, and projected back.
Geometries spanning the antimeridian are handled by the projection itself
(the local frame has no seam near the geometry); very large geometries are
buffered in the same frame, which stays accurate for distances well within
a hemisphere.
"""

from __future__ import annotations

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

_WGS84 = CRS.from_epsg(4326)


def _local_aeqd(lon: float, lat: float) -> CRS:
    return CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m +no_defs"
    )


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """Buffer a WGS84 (lon/lat) geometry by ``distance_m`` meters.

    Returns a geometry in EPSG:4326. The input is not modified.
    """
    if geom is None:
        raise ValueError("geom must be a shapely geometry")
    if geom.is_empty:
        return geom

    # Choose a center that lies on the geometry (robust for multi-part shapes
    # straddling the antimeridian, where the plain centroid can be far away).
    center = geom.representative_point()
    lon, lat = float(center.x), float(center.y)
    lon = ((lon + 180.0) % 360.0) - 180.0

    local = _local_aeqd(lon, lat)
    fwd = Transformer.from_crs(_WGS84, local, always_xy=True).transform
    inv = Transformer.from_crs(local, _WGS84, always_xy=True).transform

    projected = transform(fwd, geom)
    buffered = projected.buffer(float(distance_m))
    result = transform(inv, buffered)

    # Normalize longitudes back to [-180, 180] if the round trip drifted.
    def _norm(x, y, z=None):
        xs = ((x + 180.0) % 360.0) - 180.0
        return (xs, y) if z is None else (xs, y, z)

    return transform(_norm, result)
```