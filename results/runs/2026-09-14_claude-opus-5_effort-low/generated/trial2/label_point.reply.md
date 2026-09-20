```python
"""Label point placement for polygons.

Picks the center of the largest circle that fits inside the polygon (the
"pole of inaccessibility"), which is a far better label anchor than the
centroid: the centroid of a C-shaped or crescent polygon can fall outside
the polygon entirely, and even when it lands inside it may sit close to an
edge or in a thin neck where a text label would overflow the shape.

Importing this module has no side effects.
"""

from __future__ import annotations

import math

from shapely import maximum_inscribed_circle
from shapely.geometry import Point, Polygon
from shapely.validation import make_valid

__all__ = ["label_point"]

# Fraction of the polygon's diagonal used as the search tolerance for the
# inscribed-circle solver. Small enough that the result is visually optimal,
# large enough that the solver stays fast on detailed boundaries.
_TOLERANCE_FRACTION = 1e-3


def label_point(polygon: Polygon) -> Point:
    """Return a `Point` inside `polygon` suitable for drawing a text label.

    The point is the center of the polygon's maximum inscribed circle, i.e.
    the interior point furthest from the boundary. Holes are respected.

    Args:
        polygon: A shapely `Polygon`, in any coordinate system. Units are
            whatever the polygon's units are; no reprojection is performed.

    Returns:
        A `Point` guaranteed to lie inside the polygon (never on its
        boundary, except in degenerate zero-area cases where no strictly
        interior point exists).

    Raises:
        TypeError: If `polygon` is not a shapely `Polygon`.
        ValueError: If `polygon` is empty, or is invalid in a way that
            cannot be repaired into a polygonal geometry.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        raise ValueError("cannot place a label point in an empty polygon")

    working = polygon if polygon.is_valid else _repair(polygon)

    candidate = _inscribed_center(working)
    if candidate is not None and _is_inside(candidate, working):
        return candidate

    # Degenerate input (zero area, or a sliver whose inscribed circle
    # collapses to the boundary): fall back to a guaranteed-on-surface point.
    fallback = working.representative_point()
    return Point(fallback.x, fallback.y)


def _repair(polygon: Polygon) -> Polygon:
    """Fix a self-intersecting or otherwise invalid polygon.

    `make_valid` may split the input into several pieces; the largest one
    carries the shape the label belongs to.
    """
    repaired = make_valid(polygon)
    parts = [
        part
        for part in getattr(repaired, "geoms", [repaired])
        if isinstance(part, Polygon) and not part.is_empty
    ]
    if not parts:
        raise ValueError("polygon could not be repaired into a valid polygon")
    return max(parts, key=lambda part: part.area)


def _inscribed_center(polygon: Polygon) -> Point | None:
    """Center of the maximum inscribed circle, or None if unavailable.

    `maximum_inscribed_circle` returns the radius as a two-point LineString
    from the center to the nearest boundary point; we only want the center.
    """
    minx, miny, maxx, maxy = polygon.bounds
    diagonal = math.hypot(maxx - minx, maxy - miny)
    if not diagonal > 0.0:
        return None

    try:
        radius_line = maximum_inscribed_circle(
            polygon, tolerance=diagonal * _TOLERANCE_FRACTION
        )
    except Exception:
        # Older//unsupported GEOS builds, or a geometry the solver rejects.
        return None

    if radius_line is None or radius_line.is_empty:
        return None

    x, y = radius_line.coords[0]
    return Point(x, y)


def _is_inside(point: Point, polygon: Polygon) -> bool:
    """True if `point` lies strictly within `polygon` (not on its boundary)."""
    return bool(polygon.contains(point))
```