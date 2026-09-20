```python
"""Compute a label placement point for a polygon.

The point returned by :func:`label_point` is guaranteed to lie inside the
polygon.  The primary strategy is the "pole of inaccessibility" (the interior
point farthest from the polygon boundary), which gives a visually centred
position that avoids holes and thin necks.  Robust fallbacks are used for
degenerate or invalid input.
"""

from __future__ import annotations

from typing import Optional

from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry

try:  # shapely >= 1.7
    from shapely.algorithms.polylabel import polylabel as _polylabel
except Exception:  # pragma: no cover - extremely old shapely
    _polylabel = None

try:  # shapely >= 2.1
    from shapely import maximum_inscribed_circle as _max_inscribed_circle
except Exception:  # pragma: no cover
    _max_inscribed_circle = None

try:
    from shapely.validation import make_valid as _make_valid
except Exception:  # pragma: no cover
    _make_valid = None


def _largest_polygon(geom: BaseGeometry) -> Optional[Polygon]:
    """Extract the largest-area Polygon from any geometry (or None)."""
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


def _normalise(polygon: BaseGeometry) -> Optional[Polygon]:
    """Return a valid, non-empty Polygon to work with, or None."""
    poly = _largest_polygon(polygon)
    if poly is None:
        return None
    if not poly.is_valid:
        fixed = None
        if _make_valid is not None:
            try:
                fixed = _make_valid(poly)
            except Exception:
                fixed = None
        if fixed is None or fixed.is_empty:
            try:
                fixed = poly.buffer(0)
            except Exception:
                fixed = None
        poly = _largest_polygon(fixed) if fixed is not None else None
    if poly is None or poly.is_empty or poly.area <= 0:
        return None
    return poly


def _tolerance(poly: Polygon) -> float:
    """Precision for polylabel, scaled to the polygon's extent (any CRS)."""
    minx, miny, maxx, maxy = poly.bounds
    extent = max(maxx - minx, maxy - miny)
    if extent <= 0:
        return 1e-9
    return extent / 1000.0


def _inside(poly: Polygon, pt: Optional[BaseGeometry]) -> bool:
    return (
        pt is not None
        and isinstance(pt, Point)
        and not pt.is_empty
        and poly.contains(pt)
    )


def label_point(polygon: Polygon) -> Point:
    """Return a Point inside ``polygon`` suitable for drawing a text label.

    Works in any coordinate system: tolerances are derived from the polygon's
    own extent rather than fixed units.

    Raises:
        ValueError: if no interior point can be found (e.g. empty polygon).
    """
    if polygon is None:
        raise ValueError("polygon is None")

    poly = _normalise(polygon)
    if poly is None:
        raise ValueError("polygon is empty or has no interior")

    # Use the original geometry for the final containment check when it is
    # valid; otherwise the repaired geometry is the best we can do.
    target = polygon if isinstance(polygon, Polygon) and polygon.is_valid else poly

    # 1. Pole of inaccessibility (best visual placement).
    if _polylabel is not None:
        try:
            pt = _polylabel(poly, tolerance=_tolerance(poly))
            if _inside(target, pt):
                return pt
        except Exception:
            pass

    # 2. Centre of the maximum inscribed circle (GEOS-based alternative).
    if _max_inscribed_circle is not None:
        try:
            seg = _max_inscribed_circle(poly, tolerance=_tolerance(poly))
            if seg is not None and not seg.is_empty:
                pt = Point(seg.coords[0])
                if _inside(target, pt):
                    return pt
        except Exception:
            pass

    # 3. Centroid, if it happens to fall inside (cheap and usually pleasing).
    try:
        c = poly.centroid
        if _inside(target, c):
            return c
    except Exception:
        pass

    # 4. Shapely's guaranteed-interior representative point.
    try:
        rp = poly.representative_point()
        if _inside(target, rp):
            return rp
        if _inside(poly, rp):
            return rp
    except Exception:
        pass

    raise ValueError("could not find a point inside the polygon")


__all__ = ["label_point"]
```