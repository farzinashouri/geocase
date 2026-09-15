Bash is blocked in this session (approval denied), so I couldn't execute a verification run — the module below is written against the pyproj 3.7 / shapely 2.1 APIs without a live check.

```python
"""Geodesic area of EPSG:4326 (WGS84 longitude/latitude) polygons, in m^2.

Areas are computed with Karney's geodesic polygon-area algorithm (GeographicLib,
reached through :class:`pyproj.Geod`) directly on the WGS84 ellipsoid, so there
is no intermediate map projection to pick, and accuracy does not degrade with
latitude or polygon size.
"""

from __future__ import annotations

import numpy as np
from pyproj import Geod
from shapely import MultiPolygon, Polygon, get_coordinates

__all__ = ["area_m2"]

# The ellipsoid of EPSG:4326: a = 6378137 m, 1/f = 298.257223563.
# Building a Geod is pure computation -- no I/O, no global state mutated.
_GEOD = Geod(ellps="WGS84")


def _ring_area_m2(ring) -> float:
    """Unsigned area enclosed by one linear ring, in square meters."""
    coords = get_coordinates(ring)  # (N, 2) lon/lat float64; any Z is dropped
    if coords.shape[0] < 3:
        return 0.0
    # Contiguous copies: pyproj wants plain 1-D float64 buffers, not strided views.
    lons = np.ascontiguousarray(coords[:, 0])
    lats = np.ascontiguousarray(coords[:, 1])
    # The ring is closed implicitly, so a repeated closing vertex is harmless.
    # The returned sign only encodes winding order, which carries no area meaning
    # here, so it is discarded.
    area, _perimeter = _GEOD.polygon_area_perimeter(lons, lats)
    return abs(area)


def _polygon_area_m2(polygon: Polygon) -> float:
    """Exterior area minus the area of every hole, in square meters."""
    area = _ring_area_m2(polygon.exterior)
    for hole in polygon.interiors:
        area -= _ring_area_m2(hole)
    # Invalid input (holes overlapping or reaching outside the shell) can drive
    # this negative; an area is never negative, so clamp instead of propagating.
    return max(area, 0.0)


def area_m2(geom: Polygon | MultiPolygon) -> float:
    """Return the area of a WGS84 lon/lat polygon in square meters.

    Args:
        geom: A shapely ``Polygon`` or ``MultiPolygon`` whose coordinates are
            (longitude, latitude) degrees in EPSG:4326. Holes are subtracted and
            the parts of a ``MultiPolygon`` are summed. Empty geometries give 0.0.

    Returns:
        The ellipsoidal area in m^2, always non-negative. A 1x1 degree cell at
        the equator comes out near 1.23e10.

    Raises:
        TypeError: If ``geom`` is not a ``Polygon`` or ``MultiPolygon``.

    Notes:
        Edges are the shortest geodesics between consecutive vertices, matching
        the convention of PostGIS ``ST_Area(geography)``. Two consequences worth
        knowing: rings spanning the antimeridian need no special handling, since
        e.g. lon 179 to lon -179 is correctly read as a 2-degree step; but an
        edge meant to track a parallel (a lon/lat bounding box away from the
        equator) bows poleward slightly, so densify such edges first if the
        parallel is the intended boundary.

        Ring orientation is ignored. A ring enclosing more than half the Earth
        is therefore reported as its smaller complement -- a ring alone does not
        say which of the two regions it bounds is the inside.
    """
    if isinstance(geom, Polygon):
        parts: tuple[Polygon, ...] | object = (geom,)
    elif isinstance(geom, MultiPolygon):
        # Sum unsigned per-part areas so that parts wound in opposite directions
        # add up rather than cancelling.
        parts = geom.geoms
    else:
        raise TypeError(
            f"expected a shapely Polygon or MultiPolygon, got {type(geom).__name__}"
        )

    return float(sum(_polygon_area_m2(part) for part in parts if not part.is_empty))
```