```python
"""Compute a label placement point that is guaranteed to lie inside a polygon.

Strategy:
1. Use shapely's ``polylabel`` (pole of inaccessibility) on the largest
   polygon part, which gives the point farthest from any edge -- the
   visually best spot for a label.
2. Fall back to ``representative_point`` and then to centroid, verifying at
   each step that the candidate actually lies inside the polygon.
"""

from __future__ import annotations

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
    parts = [g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon)]
    if parts:
        return max(parts, key=lambda g: g.area)
    return None


def _tolerance(poly: Polygon) -> float:
    """Tolerance for polylabel scaled to the polygon's extent."""
    minx, miny, maxx, maxy = poly.bounds
    extent = max(maxx - minx, maxy - miny)
    if extent <= 0:
        return 1e-9
    return extent / 1000.0


def label_point(polygon: Polygon) -> Point:
    """Return a Point inside ``polygon`` suitable for drawing a text label.

    Works in any coordinate system since only the polygon's own geometry
    is used. Raises ``ValueError`` if no interior point can be found
    (e.g. an empty polygon).
    """
    if polygon is None or polygon.is_empty:
        raise ValueError("Cannot compute a label point for an empty polygon")

    original = polygon
    if not polygon.is_valid:
        polygon = make_valid(polygon)

    target = _largest_polygon(polygon)
    if target is None or target.is_empty or target.area == 0:
        target = _largest_polygon(original.buffer(0))
    if target is None or target.is_empty:
        raise ValueError("Polygon has no usable area for label placement")

    candidates = []

    try:
        candidates.append(polylabel(target, tolerance=_tolerance(target)))
    except Exception:  # noqa: BLE001 - polylabel can fail on odd inputs
        pass

    try:
        candidates.append(target.representative_point())
    except Exception:  # noqa: BLE001
        pass

    candidates.append(target.centroid)

    for candidate in candidates:
        if candidate is None or candidate.is_empty:
            continue
        pt = Point(candidate.x, candidate.y)
        if original.contains(pt) or target.contains(pt):
            return pt

    # Last resort: representative_point is contractually inside its geometry.
    pt = original.representative_point()
    if original.contains(pt) or original.intersects(pt):
        return Point(pt.x, pt.y)
    raise ValueError("Could not find a point inside the polygon")
```