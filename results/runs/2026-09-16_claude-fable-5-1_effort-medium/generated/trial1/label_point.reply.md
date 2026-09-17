```python
"""Compute a good location for drawing a text label inside a polygon.

The label point is chosen as the pole of inaccessibility (the interior
point farthest from any edge) so the label sits in the "widest" part of
the shape. If that computation is unavailable or fails, the function
falls back to shapely's guaranteed-interior representative point.
"""

from __future__ import annotations

from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

try:  # shapely >= 1.7 ships polylabel; guard anyway so import never fails.
    from shapely.ops import polylabel as _polylabel
except ImportError:  # pragma: no cover
    _polylabel = None


def _largest_polygon(geom: BaseGeometry) -> Polygon | None:
    """Return the single largest Polygon contained in ``geom``, if any."""
    if isinstance(geom, Polygon):
        return geom if not geom.is_empty else None
    if isinstance(geom, MultiPolygon):
        parts = [p for p in geom.geoms if not p.is_empty]
        return max(parts, key=lambda p: p.area) if parts else None
    if hasattr(geom, "geoms"):  # GeometryCollection or similar
        parts = [_largest_polygon(g) for g in geom.geoms]
        parts = [p for p in parts if p is not None]
        return max(parts, key=lambda p: p.area) if parts else None
    return None


def _tolerance(polygon: Polygon) -> float:
    """Pick a polylabel precision relative to the polygon's extent."""
    minx, miny, maxx, maxy = polygon.bounds
    extent = max(maxx - minx, maxy - miny)
    if extent <= 0:
        return 1e-9
    return extent / 1000.0


def label_point(polygon: Polygon) -> Point:
    """Return a Point inside ``polygon`` suitable for placing a text label.

    Works in any coordinate system since only relative geometry is used.
    Invalid polygons are repaired first; for multi-part results the
    largest part is used. Raises ValueError for empty or non-areal input.
    """
    if polygon is None or polygon.is_empty:
        raise ValueError("label_point requires a non-empty polygon")

    geom: BaseGeometry = polygon
    if not geom.is_valid:
        geom = make_valid(geom)

    poly = _largest_polygon(geom)
    if poly is None or poly.area == 0:
        raise ValueError("label_point requires a polygon with non-zero area")

    if _polylabel is not None:
        try:
            candidate = _polylabel(poly, tolerance=_tolerance(poly))
            if isinstance(candidate, Point) and poly.contains(candidate):
                return candidate
        except Exception:
            pass

    return poly.representative_point()


__all__ = ["label_point"]
```