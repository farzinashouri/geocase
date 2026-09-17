"""Compute a good interior point for placing a text label on a polygon.

The primary strategy is the "pole of inaccessibility" (the interior point
farthest from the polygon boundary), which is where a label has the most
room.  If that fails for any reason, or produces a point that does not
lie inside the polygon, we fall back to shapely's guaranteed-interior
``representative_point``.
"""

from __future__ import annotations

import math

from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.validation import make_valid

try:  # shapely >= 2.0 exposes polylabel here
    from shapely.algorithms.polylabel import polylabel as _polylabel
except ImportError:  # pragma: no cover - very old shapely
    try:
        from shapely.ops import polylabel as _polylabel
    except ImportError:  # pragma: no cover
        _polylabel = None


def _largest_polygon(geom) -> Polygon | None:
    """Return the largest Polygon contained in ``geom`` (or None)."""
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        parts = [p for p in geom.geoms if not p.is_empty]
        return max(parts, key=lambda p: p.area) if parts else None
    # GeometryCollection or other: look for polygonal members.
    if hasattr(geom, "geoms"):
        best = None
        for g in geom.geoms:
            cand = _largest_polygon(g)
            if cand is not None and (best is None or cand.area > best.area):
                best = cand
        return best
    return None


def _inside(point: Point, polygon) -> bool:
    if point is None or point.is_empty:
        return False
    x, y = point.x, point.y
    if not (math.isfinite(x) and math.isfinite(y)):
        return False
    return polygon.contains(point)


def label_point(polygon: Polygon) -> Point:
    """Return a Point inside ``polygon`` suitable for anchoring a text label.

    Works in any coordinate system: the search tolerance is derived from the
    polygon's own extent, so no assumption about units is made.

    Raises ``ValueError`` if ``polygon`` is empty or has no area.
    """
    if polygon is None or polygon.is_empty:
        raise ValueError("label_point requires a non-empty polygon")

    original = polygon

    # Repair invalid geometry (self-intersections, bowties, ...) if needed.
    work = polygon
    if not work.is_valid:
        work = _largest_polygon(make_valid(work))
    else:
        work = _largest_polygon(work)

    if work is None or work.is_empty or work.area <= 0:
        raise ValueError("label_point requires a polygon with positive area")

    # Test containment against the original if it is valid (so the promise
    # "inside the polygon" holds for what the caller passed); otherwise
    # against the repaired geometry.
    test_geom = original if original.is_valid else work

    candidates = []

    # 1. Pole of inaccessibility: point with the most clearance from edges.
    if _polylabel is not None:
        minx, miny, maxx, maxy = work.bounds
        extent = max(maxx - minx, maxy - miny)
        if extent > 0 and math.isfinite(extent):
            tolerance = extent / 1000.0
            try:
                candidates.append(_polylabel(work, tolerance=tolerance))
            except Exception:  # noqa: BLE001 - fall through to fallbacks
                pass

    # 2. Centroid is often nicest for convex shapes, if it happens to be inside.
    try:
        candidates.append(work.centroid)
    except Exception:  # noqa: BLE001
        pass

    # 3. Guaranteed-interior fallback.
    candidates.append(work.representative_point())

    for cand in candidates:
        if _inside(cand, test_geom):
            return Point(cand.x, cand.y)

    # Last resort: representative_point of the repaired geometry is interior
    # to it by construction; check against the repaired geometry.
    rp = work.representative_point()
    if _inside(rp, work):
        return Point(rp.x, rp.y)

    raise ValueError("could not find an interior point for the polygon")


__all__ = ["label_point"]