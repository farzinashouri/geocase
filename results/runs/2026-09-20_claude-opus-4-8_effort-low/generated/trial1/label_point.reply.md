```python
"""Compute a label anchor point for a polygon.

`label_point(polygon)` returns a shapely Point guaranteed to lie inside the
given polygon. It prefers the "pole of inaccessibility" (the interior point
farthest from any edge), which is where a label is most comfortably placed,
and falls back to shapely's representative point if that computation is
unavailable or fails.
"""

from shapely.geometry import Point, Polygon
from shapely.geometry.base import BaseGeometry


def label_point(polygon: Polygon) -> Point:
    """Return a Point inside ``polygon`` suitable for anchoring a text label.

    The result is the pole of inaccessibility when it can be computed, and
    otherwise a guaranteed-interior representative point. The returned point
    always lies within the polygon (touching the boundary only in degenerate
    cases where the polygon has no interior area).
    """
    if polygon is None or polygon.is_empty:
        raise ValueError("polygon must be a non-empty Polygon")

    # Repair self-intersections / invalid rings so downstream ops behave.
    geom: BaseGeometry = polygon
    if not geom.is_valid:
        geom = geom.buffer(0)

    # Degenerate (zero-area) inputs have no interior; fall back directly.
    if geom.is_empty or geom.area == 0.0:
        return polygon.representative_point()

    candidate = _pole_of_inaccessibility(geom)
    if candidate is not None and geom.contains(candidate):
        return candidate

    return geom.representative_point()


def _pole_of_inaccessibility(geom: BaseGeometry):
    """Best-effort pole of inaccessibility using shapely's polylabel."""
    try:
        from shapely.ops import polylabel
    except ImportError:
        return None

    # Tolerance relative to the polygon's extent so it scales with the CRS.
    minx, miny, maxx, maxy = geom.bounds
    extent = max(maxx - minx, maxy - miny)
    tolerance = extent / 1000.0 if extent > 0 else 0.0

    try:
        return polylabel(geom, tolerance=tolerance)
    except Exception:
        return None
```