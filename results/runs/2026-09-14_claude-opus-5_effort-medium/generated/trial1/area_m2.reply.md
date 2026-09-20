```python
"""Geodesic area of WGS84 (EPSG:4326) polygons, in square meters.

Areas are computed on the WGS84 ellipsoid with pyproj's GeographicLib
bindings, so they are accurate anywhere on Earth (poles, antimeridian,
very large or very small polygons) without picking a projection.

Importing this module has no side effects: the ``Geod`` object and the
sign-convention probe are created lazily on first use.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable, Tuple

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import orient

__all__ = ["area_m2"]


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """WGS84 ellipsoid, created once on first call."""
    return Geod(ellps="WGS84")


@lru_cache(maxsize=1)
def _ccw_sign() -> float:
    """+1 if GeographicLib reports positive area for counter-clockwise rings.

    Probed at runtime with a small square of known orientation so the module
    does not depend on the sign convention of a particular pyproj version.
    """
    lons = (0.0, 1.0, 1.0, 0.0)
    lats = (0.0, 0.0, 1.0, 1.0)  # counter-clockwise in (lon, lat)
    area, _ = _geod().polygon_area_perimeter(lons, lats)
    return 1.0 if area > 0 else -1.0


def _ring_area(coords: Iterable[Tuple[float, ...]]) -> float:
    """Signed geodesic area of one closed ring, positive when CCW."""
    lons = []
    lats = []
    for point in coords:
        lons.append(float(point[0]))
        lats.append(float(point[1]))
    if len(lons) < 3:
        return 0.0
    area, _ = _geod().polygon_area_perimeter(lons, lats)
    return area * _ccw_sign()


def _polygon_area(poly: Polygon) -> float:
    """Area of a single polygon: exterior minus its holes."""
    if poly.is_empty:
        return 0.0
    # Exterior counter-clockwise, interiors clockwise, so the signed ring
    # areas already sum to (shell - holes).
    poly = orient(poly, sign=1.0)
    total = _ring_area(poly.exterior.coords)
    for interior in poly.interiors:
        total += _ring_area(interior.coords)
    return total


def area_m2(geom) -> float:
    """Return the geodesic area of a lon/lat (EPSG:4326) polygon, in m².

    Parameters
    ----------
    geom:
        A shapely ``Polygon`` or ``MultiPolygon`` whose coordinates are
        longitude/latitude degrees in WGS84. Holes are subtracted.

    Returns
    -------
    float
        Area in square meters, always non-negative. Empty geometries give 0.0.

    Raises
    ------
    TypeError
        If ``geom`` is not a ``Polygon`` or ``MultiPolygon``.
    """
    if isinstance(geom, Polygon):
        total = _polygon_area(geom)
    elif isinstance(geom, MultiPolygon):
        total = sum(_polygon_area(part) for part in geom.geoms)
    else:
        raise TypeError(
            f"expected Polygon or MultiPolygon, got {type(geom).__name__}"
        )
    return float(abs(total))
```