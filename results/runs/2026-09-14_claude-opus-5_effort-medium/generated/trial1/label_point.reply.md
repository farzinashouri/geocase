```python
"""Compute a point suitable for drawing a text label inside a polygon.

The point returned by :func:`label_point` is the *pole of inaccessibility*: the
interior point that is furthest from the polygon's boundary.  That is a better
label anchor than the centroid, which can fall outside concave or ring-shaped
polygons, and better than ``representative_point``, which is only guaranteed to
be inside and is often jammed up against an edge.

The implementation is coordinate-system agnostic: every tolerance is derived
from the polygon's own extent, so it behaves identically for degrees, metres or
feet.  Importing this module has no side effects.
"""

from __future__ import annotations

import shapely
from shapely.geometry import Point, Polygon
from shapely.geometry.base import BaseGeometry

__all__ = ["label_point"]

# Fraction of the bounding-box diagonal used as the search tolerance for the
# maximum inscribed circle.  1e-4 puts the anchor well within sub-pixel accuracy
# for any realistic label, while keeping the search cheap.
_TOLERANCE_RATIO = 1e-4


def label_point(polygon: Polygon) -> Point:
    """Return a point inside ``polygon`` at which a label can be drawn.

    Parameters
    ----------
    polygon:
        A shapely :class:`~shapely.geometry.Polygon` in any coordinate system.
        Invalid (self-intersecting, badly nested) polygons are repaired first.

    Returns
    -------
    Point
        A point that lies inside ``polygon``.  For a polygon with no interior
        -- an empty polygon, or a zero-area sliver where no strictly interior
        point exists -- a point on the geometry is returned instead.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely ``Polygon``.
    ValueError
        If ``polygon`` is empty, or its coordinates are not finite.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        raise ValueError("cannot label an empty polygon")

    minx, miny, maxx, maxy = polygon.bounds
    if not all(map(_is_finite, (minx, miny, maxx, maxy))):
        raise ValueError("polygon has non-finite coordinates")

    working = _largest_polygon(polygon)
    if working is None:
        # The repair dissolved the polygon entirely (a pure sliver or a
        # degenerate ring); fall back to a point on the original geometry.
        return _fallback(polygon)

    diagonal = ((maxx - minx) ** 2 + (maxy - miny) ** 2) ** 0.5
    tolerance = diagonal * _TOLERANCE_RATIO

    point = _pole_of_inaccessibility(working, tolerance)
    if point is not None and working.contains(point) and polygon.covers(point):
        return point

    candidate = working.representative_point()
    if polygon.covers(candidate):
        return candidate

    return _fallback(polygon)


def _pole_of_inaccessibility(polygon: Polygon, tolerance: float) -> Point | None:
    """Centre of the largest circle that fits inside ``polygon``, or ``None``."""
    if tolerance <= 0:
        return None
    try:
        radius_line = shapely.maximum_inscribed_circle(polygon, tolerance=tolerance)
    except Exception:
        # GEOS refuses degenerate inputs; the caller falls back.
        return None
    if radius_line.is_empty:
        return None
    return Point(radius_line.coords[0])


def _largest_polygon(polygon: Polygon) -> Polygon | None:
    """Repair ``polygon`` if needed and return its largest positive-area part."""
    valid: BaseGeometry = polygon
    if not valid.is_valid:
        try:
            valid = shapely.make_valid(polygon)
        except Exception:
            return None

    best: Polygon | None = None
    for part in _polygon_parts(valid):
        if part.area > 0 and (best is None or part.area > best.area):
            best = part
    return best


def _polygon_parts(geometry: BaseGeometry):
    """Yield every ``Polygon`` inside ``geometry``, recursing into collections."""
    if geometry.is_empty:
        return
    if isinstance(geometry, Polygon):
        yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from _polygon_parts(part)


def _fallback(polygon: Polygon) -> Point:
    """Best-effort point on a polygon that has no usable interior."""
    try:
        candidate = polygon.representative_point()
        if not candidate.is_empty:
            return candidate
    except Exception:
        pass
    return Point(polygon.exterior.coords[0])


def _is_finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))
```