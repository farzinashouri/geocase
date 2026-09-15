```python
"""Geodesic area of WGS84 (EPSG:4326) geometries.

Areas are computed on the WGS84 ellipsoid with GeographicLib (via
``pyproj.Geod``) rather than by reprojecting to a planar CRS, so a single
code path stays accurate for polygons of any size, at any latitude, and
across the antimeridian.
"""

from __future__ import annotations

import numpy as np
from pyproj import Geod

# Constructing a Geod is pure: no I/O, no global state, no network.
_GEOD = Geod(ellps="WGS84")


def _ring_area_m2(coords) -> float:
    """Unsigned geodesic area of a single linear ring, in square meters."""
    arr = np.asarray(coords, dtype=float)
    if arr.ndim != 2 or arr.shape[0] < 3:
        return 0.0

    lons = arr[:, 0]
    lats = arr[:, 1]

    # Shapely rings are explicitly closed; GeographicLib wants an open ring.
    if lons[0] == lons[-1] and lats[0] == lats[-1]:
        lons = lons[:-1]
        lats = lats[:-1]
    if lons.shape[0] < 3:
        return 0.0

    if not (np.isfinite(lons).all() and np.isfinite(lats).all()):
        raise ValueError("geometry contains non-finite coordinates")

    area, _perimeter = _GEOD.polygon_area_perimeter(lons, lats)
    # The sign only encodes ring orientation, which we handle ourselves.
    return abs(float(area))


def _polygon_area_m2(polygon) -> float:
    """Exterior area minus the area of every hole, floored at zero."""
    area = _ring_area_m2(polygon.exterior.coords)
    for interior in polygon.interiors:
        area -= _ring_area_m2(interior.coords)
    return max(area, 0.0)


def area_m2(geom) -> float:
    """Return the area of a lon/lat (EPSG:4326) geometry in square meters.

    Parameters
    ----------
    geom :
        A shapely ``Polygon`` or ``MultiPolygon`` whose coordinates are
        longitude, latitude in degrees (EPSG:4326). Holes are subtracted and
        ring orientation is ignored.

    Returns
    -------
    float
        Area in square meters; ``0.0`` for empty geometries.

    Notes
    -----
    Each ring edge is treated as the geodesic between consecutive vertices,
    which is what makes antimeridian-crossing rings work without any
    splitting or shifting of longitudes. A ring that encircles a pole is
    inherently ambiguous (it bounds two regions); this returns the area of
    the region the ring's own traversal encloses, up to sign.
    """
    if geom is None:
        raise TypeError("geom must be a shapely Polygon or MultiPolygon, not None")

    geom_type = getattr(geom, "geom_type", None)
    if geom_type is None:
        raise TypeError(
            f"geom must be a shapely Polygon or MultiPolygon, got {type(geom).__name__}"
        )

    if geom.is_empty:
        return 0.0

    if geom_type == "Polygon":
        return _polygon_area_m2(geom)

    if geom_type == "MultiPolygon":
        return float(sum(_polygon_area_m2(part) for part in geom.geoms))

    raise TypeError(
        f"geom must be a Polygon or MultiPolygon, got {geom_type}"
    )
```