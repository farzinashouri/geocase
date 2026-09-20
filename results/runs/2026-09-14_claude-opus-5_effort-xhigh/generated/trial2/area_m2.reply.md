```python
"""Geodesic area of EPSG:4326 (WGS84 lon/lat) polygons, in square meters.

Areas are computed on the WGS84 ellipsoid with GeographicLib (via pyproj's
``Geod``), so they are accurate anywhere on Earth — including polygons at high
latitudes, polygons that enclose a pole, and polygons whose edges cross the
antimeridian. Edges are treated as geodesics between consecutive vertices,
which is the shortest-path interpretation: a lon step from 179 to -179 spans
2 degrees across the antimeridian, not 358 degrees back across the globe.

A closed ring divides the ellipsoid into two regions, and shapely does not
enforce a ring-orientation convention, so orientation cannot disambiguate them.
This module resolves the ambiguity by always returning the smaller region
(i.e. at most half the surface of the Earth) for each ring.

Importing this module has no side effects; the ellipsoid model is built on
first use.
"""

from __future__ import annotations

from functools import lru_cache

from pyproj import Geod

__all__ = ["area_m2"]

_SUPPORTED_TYPES = ("Polygon", "MultiPolygon")


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """Return the shared WGS84 ellipsoid model, constructing it on first use."""
    return Geod(ellps="WGS84")


def _ring_area_m2(ring) -> float:
    """Unsigned geodesic area enclosed by a single LinearRing, in m^2."""
    coords = list(ring.coords)
    # Shapely closes rings; drop the repeated vertex (GeographicLib closes for us).
    if len(coords) > 1 and coords[0] == coords[-1]:
        coords = coords[:-1]
    if len(coords) < 3:
        return 0.0
    lons = [xy[0] for xy in coords]
    lats = [xy[1] for xy in coords]
    area, _perimeter = _geod().polygon_area_perimeter(lons, lats)
    # The sign only reflects traversal direction; magnitude is the enclosed area.
    return abs(area)


def _polygon_area_m2(polygon) -> float:
    """Geodesic area of a Polygon: exterior ring minus its holes, in m^2."""
    area = _ring_area_m2(polygon.exterior)
    for hole in polygon.interiors:
        area -= _ring_area_m2(hole)
    return area


def area_m2(geom) -> float:
    """Return the area of a WGS84 lon/lat polygon in square meters.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Geometry whose coordinates are (longitude, latitude) in degrees,
        EPSG:4326. Any Z values are ignored.

    Returns
    -------
    float
        Ellipsoidal area in m^2. Empty geometries return ``0.0``.

    Raises
    ------
    TypeError
        If ``geom`` is not a Polygon or MultiPolygon.
    """
    geom_type = getattr(geom, "geom_type", None)
    if geom_type not in _SUPPORTED_TYPES:
        raise TypeError(
            f"area_m2() expects a Polygon or MultiPolygon, got {type(geom).__name__}"
        )

    if geom.is_empty:
        return 0.0

    if geom_type == "Polygon":
        return float(_polygon_area_m2(geom))

    return float(sum(_polygon_area_m2(part) for part in geom.geoms))
```