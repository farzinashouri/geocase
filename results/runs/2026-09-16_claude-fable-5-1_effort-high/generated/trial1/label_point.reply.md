```python
"""Compute a point inside a polygon that is suitable for placing a text label.

The main entry point is :func:`label_point`.  It prefers the "pole of
inaccessibility" (the interior point farthest from the polygon boundary),
which places labels away from edges and holes, and falls back to Shapely's
``representative_point`` when that is not available or does not verify as
interior.  The returned point is always strictly inside the polygon.
"""

from __future__ import annotations

import math

from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry

try:  # Available in Shapely 1.7+ / 2.x.
    from shapely.algorithms.polylabel import polylabel as _polylabel
except Exception:  # pragma: no cover - defensive import guard
    _polylabel = None

try:  # Shapely 1.8+ / 2.x.
    from shapely.validation import make_valid as _make_valid
except Exception:  # pragma: no cover - defensive import guard
    _make_valid = None


def _largest_polygon(geom: BaseGeometry) -> Polygon | None:
    """Return the largest-area Polygon contained in ``geom``, or None."""
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        parts = [p for p in geom.geoms if not p.is_empty]
    elif hasattr(geom, "geoms"):
        parts = []
        for g in geom.geoms:
            p = _largest_polygon(g)
            if p is not None:
                parts.append(p)
    else:
        return None
    if not parts:
        return None
    return max(parts, key=lambda p: p.area)


def _clean(polygon: Polygon) -> Polygon:
    """Return a valid, non-empty Polygon derived from ``polygon``."""
    if polygon.is_valid:
        return polygon
    fixed = None
    if _make_valid is not None:
        try:
            fixed = _make_valid(polygon)
        except Exception:
            fixed = None
    if fixed is None or fixed.is_empty:
        try:
            fixed = polygon.buffer(0)
        except Exception:
            fixed = None
    largest = _largest_polygon(fixed)
    if largest is None:
        raise ValueError("polygon could not be repaired into a valid area")
    return largest


def _is_inside(polygon: Polygon, point: Point) -> bool:
    """True if ``point`` is a finite point strictly inside ``polygon``."""
    if point is None or point.is_empty:
        return False
    x, y = point.x, point.y
    if not (math.isfinite(x) and math.isfinite(y)):
        return False
    return polygon.contains(point)


def _tolerance(polygon: Polygon) -> float:
    """Pick a polylabel tolerance proportional to the polygon's size."""
    minx, miny, maxx, maxy = polygon.bounds
    extent = min(maxx - minx, maxy - miny)
    if not math.isfinite(extent) or extent <= 0:
        extent = math.sqrt(polygon.area) if polygon.area > 0 else 1.0
    # 1/1000th of the smaller extent gives visually precise placement while
    # keeping the search cheap.
    return max(extent / 1000.0, 1e-12)


def label_point(polygon: Polygon) -> Point:
    """Return a Point inside ``polygon`` at which a text label can be drawn.

    Parameters
    ----------
    polygon:
        A shapely ``Polygon`` in any coordinate system (projected or
        geographic).  Invalid polygons are repaired first; if the repair
        yields several parts, the largest one is labelled.

    Returns
    -------
    shapely.geometry.Point
        A point guaranteed to lie inside the polygon.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely Polygon.
    ValueError
        If the polygon is empty or has no interior area.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(
            f"label_point expects a shapely Polygon, got {type(polygon).__name__}"
        )
    if polygon.is_empty:
        raise ValueError("cannot compute a label point for an empty polygon")

    poly = _clean(polygon)
    if poly.is_empty or poly.area <= 0:
        raise ValueError("polygon has no interior area")

    # Preferred: pole of inaccessibility (farthest interior point from the
    # boundary), which keeps labels clear of edges and holes.
    if _polylabel is not None:
        try:
            candidate = _polylabel(poly, tolerance=_tolerance(poly))
        except Exception:
            candidate = None
        if candidate is not None and _is_inside(poly, candidate):
            return Point(candidate.x, candidate.y)

    # Fallback: Shapely guarantees representative_point lies within the polygon.
    candidate = poly.representative_point()
    if _is_inside(poly, candidate):
        return Point(candidate.x, candidate.y)

    # Last resort: centroid, only if it happens to be interior.
    candidate = poly.centroid
    if _is_inside(poly, candidate):
        return Point(candidate.x, candidate.y)

    raise ValueError("could not find an interior point for the polygon")


__all__ = ["label_point"]
```