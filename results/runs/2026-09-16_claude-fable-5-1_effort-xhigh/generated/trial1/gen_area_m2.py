"""Area of shapely (Multi)Polygons given in EPSG:4326 (WGS84 longitude/latitude).

The area is evaluated directly on the WGS84 ellipsoid with Karney's geodesic
polygon algorithm (GeographicLib, exposed through ``pyproj.Geod``).  No projected
CRS is involved, so there is no projection distortion: the result is accurate for
polygons of any size at any location on Earth, including ones that straddle the
antimeridian or enclose a pole.

Conventions
-----------
* Consecutive vertices are joined by geodesics (shortest paths), the same
  convention used by PostGIS ``geography`` and BigQuery ``GEOGRAPHY``.
  Longitudes may be in [-180, 180] or [0, 360]; a jump such as 179 -> -179 is
  taken the short way across the antimeridian.
* Ring orientation is irrelevant: each ring contributes its unsigned area,
  holes are subtracted from their exterior, and MultiPolygon parts are summed.
* A ring is taken to bound the smaller of the two regions into which it divides
  the ellipsoid, so a single ring can describe at most half the Earth's surface.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import shapely
from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon

__all__ = ["area_m2"]

_LAT_TOLERANCE_DEG = 1e-9  # absorb round-off such as 90.0000000001 from reprojection


@lru_cache(maxsize=1)
def _wgs84() -> Geod:
    """Create the WGS84 ellipsoid on first use so importing this module does nothing."""
    return Geod(ellps="WGS84")


def _ring_area_m2(ring) -> float:
    """Unsigned geodesic area (m^2) enclosed by a single LinearRing."""
    coords = shapely.get_coordinates(ring)  # shape (n, 2); any Z value is dropped
    if len(coords) < 4:  # empty or degenerate ring
        return 0.0
    coords = coords[:-1]  # drop the closing vertex; the geodesic loop is closed implicitly
    if not np.all(np.isfinite(coords)):
        raise ValueError("ring contains non-finite coordinates")
    lons = coords[:, 0]
    lats = coords[:, 1]
    if np.any(np.abs(lats) > 90.0 + _LAT_TOLERANCE_DEG):
        raise ValueError(
            "latitude outside [-90, 90]; coordinates must be EPSG:4326 (lon, lat) degrees"
        )
    lats = np.clip(lats, -90.0, 90.0)
    area, _perimeter = _wgs84().polygon_area_perimeter(lons, lats)
    return abs(float(area))


def _polygon_area_m2(poly: Polygon) -> float:
    """Geodesic area (m^2) of one Polygon: exterior ring minus all holes."""
    if poly.is_empty:
        return 0.0
    area = _ring_area_m2(poly.exterior)
    for hole in poly.interiors:
        area -= _ring_area_m2(hole)
    return max(area, 0.0)  # guard against round-off when holes fill the exterior


def area_m2(geom) -> float:
    """Return the area in square metres of a WGS84 lon/lat Polygon or MultiPolygon.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Geometry whose coordinates are (longitude, latitude) in degrees, EPSG:4326.
        A third (Z) coordinate, if present, is ignored.

    Returns
    -------
    float
        Area on the WGS84 ellipsoid in square metres (0.0 for an empty geometry).

    Raises
    ------
    TypeError
        If ``geom`` is not a Polygon or MultiPolygon.
    ValueError
        If any coordinate is non-finite or a latitude lies outside [-90, 90].
    """
    if isinstance(geom, Polygon):
        return float(_polygon_area_m2(geom))
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area_m2(part) for part in geom.geoms))
    raise TypeError(
        f"area_m2 expects a shapely Polygon or MultiPolygon, got {type(geom).__name__}"
    )