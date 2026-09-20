```python
"""Geodesic length of EPSG:4326 (WGS84 lon/lat) linework, in meters.

Planar length (``shapely``'s ``LineString.length``) is meaningless on
lon/lat coordinates, and a single projected CRS (UTM zone, Web Mercator,
...) is only accurate in a limited region. Instead, each segment is
measured as a geodesic on the WGS84 ellipsoid via ``pyproj.Geod``, which
is accurate to roughly nanometer level anywhere on Earth.

Notes / assumptions:
  * Coordinate order is (longitude, latitude), matching EPSG:4326 as it
    is conventionally stored in GeoJSON, shapefiles and shapely.
  * Any Z (or M) values are ignored; the result is the length of the
    ground track, not the 3-D slope distance.
  * Each consecutive coordinate pair is joined by the *shorter* geodesic,
    so segments that cross the antimeridian are handled correctly as long
    as the two endpoints are less than 180 degrees of longitude apart
    (the normal case for real linework). A segment intended to span more
    than half the globe cannot be expressed unambiguously by two points
    and must be densified by the caller.
"""

from __future__ import annotations

from functools import lru_cache

from pyproj import Geod

__all__ = ["length_m"]


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """Return a shared WGS84 ``Geod``, built on first use.

    Constructed lazily and cached so that importing this module does
    nothing but define names.
    """
    return Geod(ellps="WGS84")


def length_m(line) -> float:
    """Return the geodesic length of ``line`` in meters.

    Parameters
    ----------
    line:
        A shapely ``LineString`` (or ``LinearRing``) whose coordinates
        are longitude/latitude degrees in EPSG:4326.

    Returns
    -------
    float
        Length along the WGS84 ellipsoid, in meters. Empty geometries and
        single-point degenerate geometries return ``0.0``.

    Raises
    ------
    TypeError
        If ``line`` does not expose a coordinate sequence (e.g. a
        ``Polygon`` or ``MultiLineString``, which have no unambiguous
        single coordinate list).
    """
    try:
        coords = list(line.coords)
    except (AttributeError, NotImplementedError) as exc:
        raise TypeError(
            "length_m() expects a shapely LineString or LinearRing, "
            f"got {type(line).__name__}"
        ) from exc

    if len(coords) < 2:
        return 0.0

    lons = [float(c[0]) for c in coords]
    lats = [float(c[1]) for c in coords]

    # line_length sums the geodesic distances between consecutive points;
    # abs() guards against any signed-zero / tiny-negative artifact.
    return abs(float(_geod().line_length(lons, lats)))
```