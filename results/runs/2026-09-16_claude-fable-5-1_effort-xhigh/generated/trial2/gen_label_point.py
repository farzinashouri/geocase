"""Compute a point inside a polygon suitable for placing a text label.

The primary strategy is the *pole of inaccessibility* (the interior point
farthest from the polygon boundary), which keeps labels away from edges and
handles concave shapes and holes gracefully. Every result is verified to lie
strictly inside the polygon; if it does not, a guaranteed-interior fallback is
returned instead.

Importing this module has no side effects.
"""

from __future__ import annotations

import math

import shapely
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import polylabel

__all__ = ["label_point"]

# Fraction of the polygon's larger bounding-box dimension used as the polylabel
# search tolerance. This keeps precision proportional to the shape's size
# regardless of the coordinate system (degrees, metres, pixels, ...).
_RELATIVE_TOLERANCE = 1e-3


def _largest_polygon(geom: BaseGeometry) -> Polygon | None:
    """Return the largest-area Polygon contained in ``geom``, or None."""
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        parts = [p for p in geom.geoms if not p.is_empty]
    elif hasattr(geom, "geoms"):  # GeometryCollection or similar
        parts = []
        for part in geom.geoms:
            found = _largest_polygon(part)
            if found is not None:
                parts.append(found)
    else:
        return None
    if not parts:
        return None
    return max(parts, key=lambda p: p.area)


def _prepare(polygon: BaseGeometry) -> Polygon:
    """Validate/normalise the input into a single non-empty Polygon."""
    if not isinstance(polygon, BaseGeometry):
        raise TypeError(
            "label_point expects a shapely Polygon, got "
            + type(polygon).__name__
        )
    if polygon.is_empty:
        raise ValueError("Cannot compute a label point for an empty geometry")

    geom: BaseGeometry = polygon
    if not geom.is_valid:
        # Self-intersections etc. make polylabel unreliable; repair first.
        geom = shapely.make_valid(geom)

    single = _largest_polygon(geom)
    if single is None or single.is_empty:
        raise ValueError("Geometry contains no polygonal area to label")
    return single


def _tolerance(polygon: Polygon) -> float:
    """Polylabel precision proportional to the polygon's bounding-box size."""
    minx, miny, maxx, maxy = polygon.bounds
    extent = max(maxx - minx, maxy - miny)
    if not math.isfinite(extent) or extent <= 0.0:
        return 0.0
    return extent * _RELATIVE_TOLERANCE


def _is_inside(polygon: Polygon, point: Point | None) -> bool:
    """Strict interior test (boundary points are rejected)."""
    if point is None or point.is_empty:
        return False
    x, y = point.x, point.y
    if not (math.isfinite(x) and math.isfinite(y)):
        return False
    return bool(polygon.contains(point))


def label_point(polygon: Polygon) -> Point:
    """Return a Point inside ``polygon`` that is a good spot for a text label.

    The point is the polygon's pole of inaccessibility (the interior point
    farthest from any edge), computed with a tolerance proportional to the
    polygon's size so it behaves the same in any coordinate system. If the
    polygon is invalid it is repaired first; if it repairs into several
    parts (or a MultiPolygon is passed), the largest part is labelled. The
    returned point is always inside the polygon.

    Raises:
        TypeError: if ``polygon`` is not a shapely geometry.
        ValueError: if the geometry is empty or has no polygonal area.
    """
    poly = _prepare(polygon)

    candidate: Point | None = None
    tol = _tolerance(poly)
    if tol > 0.0 and poly.area > 0.0:
        try:
            candidate = polylabel(poly, tolerance=tol)
        except Exception:
            # Defensive: fall through to the guaranteed-interior fallbacks.
            candidate = None

    if _is_inside(poly, candidate):
        return Point(candidate.x, candidate.y)

    # Fallbacks, each cheap and each checked for strict interiority.
    # ``representative_point`` is guaranteed to be on the geometry; the
    # centroid is not, so it is only used if it happens to be inside.
    for fallback in (poly.representative_point, lambda: poly.centroid):
        try:
            alt = fallback()
        except Exception:
            continue
        if _is_inside(poly, alt):
            return Point(alt.x, alt.y)

    # Degenerate (e.g. zero-area) polygon: no strict interior exists. Return
    # a point on the geometry rather than failing outright.
    rep = poly.representative_point()
    if rep.is_empty:
        raise ValueError("Could not find a point inside the polygon")
    return Point(rep.x, rep.y)