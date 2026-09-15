```python
"""Label placement for polygons.

`label_point` returns a point that lies inside a polygon and is a reasonable
place to draw a text label: it aims for the *pole of inaccessibility* (the
interior point furthest from the boundary), which keeps the label away from
edges and out of holes, and falls back to guaranteed-interior points if that
search fails.

The polygon is treated in its own planar coordinates, so the function works
for projected units or lon/lat degrees alike; no reprojection is performed and
the result is returned in the input coordinate system.
"""

from __future__ import annotations

import math

import shapely
from shapely.errors import GEOSException, TopologicalError
from shapely.geometry import Point, Polygon
from shapely.ops import polylabel

__all__ = ["label_point"]

# Search precision for the pole of inaccessibility, relative to the polygon's
# larger bounding-box side. Relative (rather than absolute) so the cost of the
# search is independent of the coordinate system's units.
_TOLERANCE_RATIO = 1e-3

# Above this vertex count, run the search against a simplified copy; the
# candidate is still validated against the full-resolution polygon.
_SIMPLIFY_VERTEX_LIMIT = 2_000

_POLYLABEL_ERRORS = (TopologicalError, GEOSException, ValueError, ZeroDivisionError)


def label_point(polygon: Polygon) -> Point:
    """Return a `Point` inside `polygon` suitable for drawing a label.

    The point is placed at (an approximation of) the polygon's pole of
    inaccessibility, so it stays clear of the boundary and of any holes. The
    returned point is verified to be contained by the polygon before it is
    handed back.

    Invalid input geometry is repaired with `shapely.make_valid` and the
    largest resulting polygonal part is labelled.

    Raises:
        TypeError: if `polygon` is not a shapely `Polygon`.
        ValueError: if the polygon is empty, degenerate (no positive area, so
            no point can lie inside it), or has non-finite coordinates.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        raise ValueError("cannot label an empty polygon")

    working = polygon if polygon.is_valid else _largest_polygon(shapely.make_valid(polygon))
    if working is None or working.is_empty or working.area <= 0.0:
        raise ValueError("polygon has no interior area, so no point lies inside it")
    if not all(math.isfinite(v) for v in working.bounds):
        raise ValueError("polygon has non-finite coordinates")

    candidates = (
        _pole_of_inaccessibility(working),
        working.representative_point(),
        working.centroid,
    )
    for candidate in candidates:
        if candidate is None or candidate.is_empty:
            continue
        if working.contains(candidate):
            return candidate

    # representative_point() is documented to lie on the surface, so reaching
    # here means the geometry is pathological in a way we should not paper over.
    raise ValueError("could not find a point inside the polygon")


def _pole_of_inaccessibility(polygon: Polygon) -> Point | None:
    """Best-effort interior point furthest from the boundary, or None."""
    tolerance = _tolerance(polygon)
    if tolerance <= 0.0:
        return None

    search = polygon
    if shapely.get_num_coordinates(polygon) > _SIMPLIFY_VERTEX_LIMIT:
        simplified = polygon.simplify(tolerance / 2.0)
        if isinstance(simplified, Polygon) and simplified.is_valid and not simplified.is_empty:
            search = simplified

    try:
        return polylabel(search, tolerance)
    except _POLYLABEL_ERRORS:
        # Slivers and other near-degenerate shapes can starve the cell queue;
        # the caller falls back to a guaranteed-interior point.
        return None


def _tolerance(polygon: Polygon) -> float:
    minx, miny, maxx, maxy = polygon.bounds
    extent = max(maxx - minx, maxy - miny)
    if not math.isfinite(extent) or extent <= 0.0:
        return 0.0
    return extent * _TOLERANCE_RATIO


def _largest_polygon(geometry) -> Polygon | None:
    """Largest-area non-empty Polygon within `geometry`, or None."""
    if isinstance(geometry, Polygon):
        return None if geometry.is_empty else geometry

    best: Polygon | None = None
    for part in getattr(geometry, "geoms", ()):
        candidate = _largest_polygon(part)
        if candidate is not None and (best is None or candidate.area > best.area):
            best = candidate
    return best
```