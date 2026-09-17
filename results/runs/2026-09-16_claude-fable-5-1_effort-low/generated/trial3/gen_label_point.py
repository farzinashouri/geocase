"""Compute a point inside a polygon suitable for placing a text label.

The strategy follows the "pole of inaccessibility" idea (the point inside
the polygon farthest from its boundary). Shapely 2.x exposes this as
``Polygon.polylabel`` / ``shapely.maximum_inscribed_circle``; a fallback
chain of ``representative_point`` and a robust boundary-distance search is
used when those are unavailable or fail. The result is always guaranteed
to lie inside the input polygon.
"""

from __future__ import annotations

import math

import shapely
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

__all__ = ["label_point"]


def _largest_polygon(geom: BaseGeometry) -> Polygon | None:
    """Return the largest-area Polygon contained in ``geom`` (or None)."""
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        parts = [p for p in geom.geoms if not p.is_empty]
    elif hasattr(geom, "geoms"):
        parts = []
        for g in geom.geoms:
            sub = _largest_polygon(g)
            if sub is not None:
                parts.append(sub)
    else:
        return None
    if not parts:
        return None
    return max(parts, key=lambda p: p.area)


def _tolerance(polygon: Polygon) -> float:
    """Pick a polylabel precision relative to the polygon's size."""
    minx, miny, maxx, maxy = polygon.bounds
    extent = max(maxx - minx, maxy - miny)
    if not math.isfinite(extent) or extent <= 0:
        return 1e-9
    return extent * 1e-3


def _pole_of_inaccessibility(polygon: Polygon) -> Point | None:
    """Try shapely's polylabel / maximum inscribed circle."""
    tol = _tolerance(polygon)
    try:
        pt = shapely.maximum_inscribed_circle(polygon, tol)
        # maximum_inscribed_circle returns a LineString from the centre to
        # the nearest boundary point; the centre is the first coordinate.
        if pt is not None and not pt.is_empty:
            coords = list(pt.coords)
            if coords:
                return Point(coords[0][:2])
    except Exception:
        pass
    try:
        from shapely.ops import polylabel

        pt = polylabel(polygon, tolerance=tol)
        if pt is not None and not pt.is_empty:
            return Point(pt.x, pt.y)
    except Exception:
        pass
    return None


def _grid_search(polygon: Polygon) -> Point | None:
    """Brute-force fallback: densest interior sample farthest from boundary."""
    minx, miny, maxx, maxy = polygon.bounds
    if not all(math.isfinite(v) for v in (minx, miny, maxx, maxy)):
        return None
    boundary = polygon.boundary
    best: Point | None = None
    best_d = -1.0
    n = 40
    for i in range(1, n):
        x = minx + (maxx - minx) * i / n
        for j in range(1, n):
            y = miny + (maxy - miny) * j / n
            p = Point(x, y)
            if polygon.contains(p):
                d = boundary.distance(p)
                if d > best_d:
                    best_d = d
                    best = p
    return best


def label_point(polygon: Polygon) -> Point:
    """Return a shapely ``Point`` inside ``polygon`` suitable for a label.

    The point is chosen to be as far from the polygon's boundary as is
    practical (the pole of inaccessibility), which keeps labels away from
    edges and holes. For a MultiPolygon, the largest part is used. The
    returned point is always strictly inside the (valid form of the) input.

    Raises:
        TypeError: if ``polygon`` is not a shapely geometry.
        ValueError: if the polygon is empty or has no interior area.
    """
    if not isinstance(polygon, BaseGeometry):
        raise TypeError(
            f"label_point expects a shapely geometry, got {type(polygon).__name__}"
        )
    if polygon.is_empty:
        raise ValueError("cannot compute a label point for an empty geometry")

    target = polygon
    if not target.is_valid:
        target = make_valid(target)
    target = _largest_polygon(target)
    if target is None or target.is_empty or target.area <= 0:
        raise ValueError("geometry has no polygonal area to place a label in")

    candidates = []

    pole = _pole_of_inaccessibility(target)
    if pole is not None:
        candidates.append(pole)

    try:
        candidates.append(target.representative_point())
    except Exception:
        pass

    try:
        candidates.append(target.centroid)
    except Exception:
        pass

    for cand in candidates:
        if cand is not None and not cand.is_empty and target.contains(cand):
            return Point(cand.x, cand.y)

    grid = _grid_search(target)
    if grid is not None and target.contains(grid):
        return Point(grid.x, grid.y)

    # Last resort: nudge the representative point toward the interior. This
    # branch should be unreachable for any non-degenerate polygon, but it
    # keeps the inside-guarantee explicit.
    rp = target.representative_point()
    if target.contains(rp):
        return Point(rp.x, rp.y)
    raise ValueError("unable to find an interior point for the given polygon")