"""Compute a point inside a polygon suitable for drawing a text label.

The strategy follows the "pole of inaccessibility" idea: prefer the point
farthest from the polygon boundary (via shapely's polylabel), then fall back
to representative_point, and finally to a manual search. The returned point
is always verified to lie inside the polygon.
"""

from __future__ import annotations

import math

from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.ops import polylabel
from shapely.validation import make_valid


def _largest_polygon(geom) -> Polygon | None:
    """Return the largest Polygon component of ``geom``, or None."""
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        return max(geom.geoms, key=lambda g: g.area)
    if hasattr(geom, "geoms"):
        polys = [g for g in geom.geoms if isinstance(g, Polygon) and not g.is_empty]
        if polys:
            return max(polys, key=lambda g: g.area)
    return None


def _tolerance_for(polygon: Polygon) -> float:
    """Pick a polylabel tolerance relative to the polygon's extent."""
    minx, miny, maxx, maxy = polygon.bounds
    extent = max(maxx - minx, maxy - miny)
    if not math.isfinite(extent) or extent <= 0:
        return 1e-9
    return extent / 1000.0


def _inside(polygon: Polygon, point: Point) -> bool:
    return point is not None and not point.is_empty and polygon.contains(point)


def _grid_search(polygon: Polygon) -> Point | None:
    """Brute-force fallback: scan a grid and return the interior point
    farthest from the boundary."""
    minx, miny, maxx, maxy = polygon.bounds
    boundary = polygon.boundary
    best = None
    best_dist = -1.0
    for n in (10, 30, 100):
        for i in range(1, n):
            x = minx + (maxx - minx) * i / n
            for j in range(1, n):
                y = miny + (maxy - miny) * j / n
                p = Point(x, y)
                if polygon.contains(p):
                    d = boundary.distance(p)
                    if d > best_dist:
                        best_dist = d
                        best = p
        if best is not None:
            return best
    return None


def label_point(polygon: Polygon) -> Point:
    """Return a Point inside ``polygon`` at which a label can be placed.

    Works in any coordinate system (planar or geographic) since only the
    polygon's own coordinates are used. Invalid geometries are repaired and,
    for multi-part results, the largest part is used.

    Raises:
        ValueError: if the polygon is empty or has no interior.
    """
    if polygon is None or polygon.is_empty:
        raise ValueError("Cannot compute a label point for an empty polygon")

    work = polygon
    if not work.is_valid:
        work = _largest_polygon(make_valid(work))
        if work is None:
            work = polygon.buffer(0)
            work = _largest_polygon(work)
    if work is None or work.is_empty or work.area <= 0:
        raise ValueError("Polygon has no interior area to place a label in")

    candidates = []

    # 1. Pole of inaccessibility: visually best spot for a label.
    try:
        candidates.append(polylabel(work, tolerance=_tolerance_for(work)))
    except Exception:
        pass

    # 2. Shapely's guaranteed-interior point.
    try:
        candidates.append(work.representative_point())
    except Exception:
        pass

    # 3. Centroid, in case it happens to be inside (cheap and central).
    try:
        candidates.append(work.centroid)
    except Exception:
        pass

    for cand in candidates:
        if _inside(work, cand) and _inside(polygon, cand):
            return Point(cand.x, cand.y)
    for cand in candidates:
        if _inside(work, cand):
            return Point(cand.x, cand.y)

    # 4. Last resort: grid search.
    found = _grid_search(work)
    if found is not None:
        return Point(found.x, found.y)

    raise ValueError("Could not find an interior point for the polygon")