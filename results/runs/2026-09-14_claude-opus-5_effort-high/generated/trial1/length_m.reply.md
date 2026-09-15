```python
"""Geodesic length of WGS84 (EPSG:4326) linestrings.

Uses pyproj's Geod, which solves the inverse geodesic problem on the WGS84
ellipsoid (Karney's algorithm). This is accurate to sub-millimeter anywhere on
Earth, including near the poles and across the antimeridian, and avoids the
distortion of measuring in a projected or planar CRS.
"""

from __future__ import annotations

from pyproj import Geod

__all__ = ["length_m"]

# Constructing a Geod is pure and cheap: no I/O, no global state mutation.
_GEOD = Geod(ellps="WGS84")


def length_m(line) -> float:
    """Return the geodesic length of ``line`` in meters.

    Parameters
    ----------
    line : shapely.geometry.LineString
        Coordinates ordered (longitude, latitude) in degrees, EPSG:4326.
        A Z ordinate, if present, is ignored.

    Returns
    -------
    float
        Length in meters along the WGS84 ellipsoid. Empty geometries and
        single-point lines have length 0.0.
    """
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0

    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    # line_length sums the geodesic distance between consecutive vertices and
    # handles antimeridian-crossing segments via the inverse solution.
    return float(_GEOD.line_length(lons, lats))
```