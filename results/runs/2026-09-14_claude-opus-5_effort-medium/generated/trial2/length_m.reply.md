```python
"""Geodesic length of WGS84 (EPSG:4326) linestrings.

`length_m` measures a lon/lat `LineString` on the WGS84 ellipsoid, so it is
accurate anywhere on Earth -- including at high latitudes and across the
antimeridian -- unlike `shapely`'s planar `LineString.length`, which treats
degrees as if they were a flat Cartesian plane.
"""

from __future__ import annotations

import math

from pyproj import Geod

__all__ = ["length_m"]

# Constructing a Geod is pure computation (no I/O), so this is import-safe.
_GEOD = Geod(ellps="WGS84")


def length_m(line) -> float:
    """Return the geodesic length of `line` in meters.

    Parameters
    ----------
    line :
        A shapely ``LineString`` (or ``LinearRing``) whose coordinates are
        ``(longitude, latitude)`` in degrees, EPSG:4326. Any Z values are
        ignored: the result is the length along the ellipsoid surface.

    Returns
    -------
    float
        Length in meters. Empty or single-point geometries give ``0.0``.

    Notes
    -----
    Consecutive vertices are joined by geodesics (the shortest path on the
    ellipsoid), which is the standard interpretation of a WGS84 linestring.
    A segment spanning the antimeridian is therefore measured the short way
    around rather than wrapping the globe.
    """
    coords = getattr(line, "coords", None)
    if coords is None:
        raise TypeError(
            f"length_m expects a shapely LineString, got {type(line).__name__}"
        )

    lons: list[float] = []
    lats: list[float] = []
    for point in coords:
        lon, lat = float(point[0]), float(point[1])
        if not (math.isfinite(lon) and math.isfinite(lat)):
            raise ValueError(f"non-finite coordinate in line: ({lon}, {lat})")
        lons.append(lon)
        lats.append(lat)

    if len(lons) < 2:
        return 0.0

    return float(_GEOD.line_length(lons, lats))
```