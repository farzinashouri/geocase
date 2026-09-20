```python
"""Geodesic area of WGS84 (EPSG:4326) polygons, in square meters.

Uses pyproj's geodesic polygon area, which integrates on the WGS84
ellipsoid directly from longitude/latitude vertices.  Unlike an
equal-area map projection, it needs no per-geometry projection choice
and stays accurate for polygons anywhere on Earth, including ones that
cross the antimeridian or sit at the poles.
"""

from __future__ import annotations

from functools import lru_cache

from shapely.geometry.base import BaseGeometry

__all__ = ["area_m2"]


@lru_cache(maxsize=1)
def _geod():
    # Imported and constructed lazily so importing this module does nothing.
    from pyproj import Geod

    return Geod(ellps="WGS84")


def _ring_area_m2(coords) -> float:
    """Unsigned geodesic area enclosed by a single linear ring."""
    lons = [float(c[0]) for c in coords]
    lats = [float(c[1]) for c in coords]

    # Rings from shapely repeat the first vertex; pyproj closes them itself.
    if len(lons) > 1 and lons[0] == lons[-1] and lats[0] == lats[-1]:
        lons, lats = lons[:-1], lats[:-1]
    if len(lons) < 3:
        return 0.0

    area, _perimeter = _geod().polygon_area_perimeter(lons, lats)
    # Sign only reports ring winding order, which we handle ourselves.
    return abs(area)


def _polygon_area_m2(polygon) -> float:
    area = _ring_area_m2(polygon.exterior.coords)
    for hole in polygon.interiors:
        area -= _ring_area_m2(hole.coords)
    return area


def area_m2(geom: BaseGeometry) -> float:
    """Return the area of a lon/lat ``Polygon``/``MultiPolygon`` in m².

    Parameters
    ----------
    geom:
        A shapely ``Polygon`` or ``MultiPolygon`` whose coordinates are
        longitude/latitude degrees in EPSG:4326.

    Returns
    -------
    float
        Area in square meters, always non-negative.
    """
    if geom is None:
        raise TypeError("geom must be a shapely Polygon or MultiPolygon, got None")

    geom_type = getattr(geom, "geom_type", None)
    if geom_type not in ("Polygon", "MultiPolygon"):
        raise TypeError(
            "geom must be a shapely Polygon or MultiPolygon, got "
            f"{geom_type or type(geom).__name__}"
        )

    if geom.is_empty:
        return 0.0

    if geom_type == "Polygon":
        return float(_polygon_area_m2(geom))

    return float(sum(_polygon_area_m2(part) for part in geom.geoms))
```