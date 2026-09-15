Bash was blocked by permissions, so I couldn't run a verification pass — the module below is written but unexecuted.

```python
"""Geodesic length of EPSG:4326 (WGS84 lon/lat) linestrings, in meters.

Each segment between consecutive vertices is measured as a geodesic on the
WGS84 ellipsoid (Karney's algorithm, via pyproj), which is accurate to
sub-millimeter anywhere on Earth -- poles, long spans, and antimeridian
crossings included -- and needs no projected CRS or UTM zone selection.
"""

from __future__ import annotations

from functools import lru_cache

from pyproj import Geod

__all__ = ["length_m"]


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """WGS84 ellipsoid, built on first call so importing this module is inert."""
    return Geod(ellps="WGS84")


def length_m(line) -> float:
    """Return the geodesic length of ``line`` in meters.

    Parameters
    ----------
    line
        A shapely ``LineString`` (or ``LinearRing``) whose coordinates are
        ``(longitude, latitude)`` degrees in EPSG:4326. Any Z values are
        ignored: the result is ground length, not slope length.

    Returns
    -------
    float
        Length in meters. Empty or single-vertex geometries return ``0.0``.

    Notes
    -----
    A segment is taken to be the shorter geodesic between its two endpoints,
    the usual reading of a straight EPSG:4326 segment. So a segment from
    lon 179.5 to lon -179.5 measures ~111 km across the antimeridian rather
    than ~40000 km the long way around.

    Raises
    ------
    ValueError
        If a latitude falls outside [-90, 90], which usually means the
        coordinates were built in (lat, lon) order.
    """
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0

    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    for lat in lats:
        if not -90.0 <= lat <= 90.0:
            raise ValueError(
                f"latitude {lat!r} outside [-90, 90]; "
                "coordinates must be (longitude, latitude) in EPSG:4326"
            )

    return float(_geod().line_length(lons, lats))
```