```python
"""Label placement for polygons.

Provides ``label_point(polygon)``, which returns a shapely ``Point`` that lies
strictly inside the given polygon and is a good anchor for drawing a text
label (the pole of inaccessibility, i.e. the interior point farthest from the
polygon boundary). Works in any coordinate system since only relative
geometry is used.
"""

from __future__ import annotations

from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

try:  # shapely >= 2.1
    from shapely import maximum_inscribed_circle as _max_inscribed_circle
except ImportError:  # pragma: no cover - older shapely
    _max_inscribed_circle = None

try:
    from shapely.algorithms.polylabel import polylabel as _polylabel
except ImportError:  # pragma: no cover
    _polylabel = None


def _largest_polygon(geom: BaseGeometry) -> Polygon | None:
    """Return the largest Polygon contained in ``geom`` (or None)."""
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        return max(geom.geoms, key=lambda g: g.area)
    if hasattr(geom, "geoms"):
        candidates = [p for p in (_largest_polygon(g) for g in geom.geoms) if p is not None]
        if candidates:
            return max(candidates, key=lambda g: g.area)
    return None


def _tolerance(poly: Polygon) -> float:
    minx, miny, maxx, maxy = poly.bounds
    extent = max(maxx - minx, maxy - miny)
    return extent / 1000.0 if extent > 0 else 1e-9


def label_point(polygon: Polygon) -> Point:
    """Return a Point inside ``polygon`` suitable for anchoring a text label.

    The point is the (approximate) pole of inaccessibility: the interior
    point farthest from the polygon's boundary. For multi-part or invalid
    input, the largest valid part is used. Falls back to
    ``representative_point`` if the primary algorithm fails.

    Raises ``ValueError`` if no interior point can be found (e.g. empty or
    fully degenerate input).
    """
    if polygon is None or polygon.is_empty:
        raise ValueError("label_point requires a non-empty polygon")

    geom: BaseGeometry = polygon
    if not geom.is_valid:
        geom = make_valid(geom)

    poly = _largest_polygon(geom)
    if poly is None or poly.is_empty or poly.area <= 0:
        # Degenerate (zero-area) input: try a tiny buffer, then give up.
        fallback = polygon.buffer(_tolerance(polygon) if not polygon.is_empty else 0)
        poly = _largest_polygon(fallback)
        if poly is None or poly.is_empty or poly.area <= 0:
            raise ValueError("polygon has no interior in which to place a label")

    tol = _tolerance(poly)
    candidate: Point | None = None

    if _max_inscribed_circle is not None:
        try:
            radius_line = _max_inscribed_circle(poly, tol)
            if radius_line is not None and not radius_line.is_empty:
                candidate = Point(radius_line.coords[0])
        except Exception:
            candidate = None

    if candidate is None and _polylabel is not None:
        try:
            candidate = _polylabel(poly, tolerance=tol)
        except Exception:
            candidate = None

    if candidate is None or candidate.is_empty or not poly.contains(candidate):
        candidate = poly.representative_point()

    if not poly.contains(candidate):
        # Last resort: check the original polygon directly.
        candidate = polygon.representative_point()
        if not polygon.contains(candidate):
            raise ValueError("could not find a point inside the polygon")

    return candidate


__all__ = ["label_point"]
```