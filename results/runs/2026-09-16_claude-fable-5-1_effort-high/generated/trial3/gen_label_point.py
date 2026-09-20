"""Compute a point inside a polygon that is suitable for placing a text label.

The primary strategy is the "pole of inaccessibility" (the interior point
farthest from the boundary), computed with shapely's ``polylabel``.  That
point is well suited for labels because it sits in the widest part of the
shape rather than in a thin appendage or, for concave shapes, outside the
polygon altogether (as the centroid can).

Fallbacks are applied for degenerate or invalid geometry so that the function
always returns a point that lies inside (or, for zero-area input, on) the
polygon.
"""

from __future__ import annotations

import math

from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.validation import make_valid

try:  # shapely >= 2.0
    from shapely.algorithms.polylabel import polylabel as _polylabel
except ImportError:  # pragma: no cover - older shapely layout
    from shapely.ops import polylabel as _polylabel  # type: ignore[no-redef]

__all__ = ["label_point"]

# Fraction of the polygon's larger bounding-box dimension used as the
# polylabel precision.  Making this relative keeps the algorithm sensible for
# any coordinate system (degrees, metres, pixels, ...).
_TOLERANCE_FRACTION = 1e-3


def _largest_polygon(geometry) -> Polygon | None:
    """Return the largest-area Polygon contained in ``geometry``, or None."""
    if geometry is None or geometry.is_empty:
        return None
    if isinstance(geometry, Polygon):
        return geometry
    if isinstance(geometry, MultiPolygon):
        parts = [p for p in geometry.geoms if not p.is_empty]
    elif hasattr(geometry, "geoms"):  # GeometryCollection etc.
        parts = []
        for part in geometry.geoms:
            candidate = _largest_polygon(part)
            if candidate is not None:
                parts.append(candidate)
    else:
        return None
    if not parts:
        return None
    return max(parts, key=lambda p: p.area)


def _tolerance(polygon: Polygon) -> float:
    minx, miny, maxx, maxy = polygon.bounds
    extent = max(maxx - minx, maxy - miny)
    if not math.isfinite(extent) or extent <= 0.0:
        return 1.0
    return extent * _TOLERANCE_FRACTION


def _inside(polygon: Polygon, point: Point) -> bool:
    """True if ``point`` is a finite point lying inside/on ``polygon``."""
    if point is None or point.is_empty:
        return False
    x, y = point.x, point.y
    if not (math.isfinite(x) and math.isfinite(y)):
        return False
    return polygon.covers(point)


def label_point(polygon: Polygon) -> Point:
    """Return a Point inside ``polygon`` at which a text label can be drawn.

    Parameters
    ----------
    polygon:
        A shapely ``Polygon`` in any coordinate system.  Invalid polygons are
        repaired first; if the input is a multi-part geometry the largest
        part is used.

    Returns
    -------
    shapely.geometry.Point
        A point guaranteed to lie within the polygon.

    Raises
    ------
    ValueError
        If the input is empty, or no usable polygon can be recovered from it.
    """
    if polygon is None or polygon.is_empty:
        raise ValueError("label_point() requires a non-empty polygon")

    original = _largest_polygon(polygon)
    if original is None:
        raise ValueError("label_point() requires a Polygon (or MultiPolygon)")

    working = original
    if not working.is_valid:
        repaired = _largest_polygon(make_valid(working))
        if repaired is not None and repaired.area > 0.0:
            working = repaired

    # Reference geometry used to check candidates.  Prefer the original
    # geometry when it is valid so the returned point is inside *that*.
    reference = original if original.is_valid else working

    # 1. Pole of inaccessibility (best label position).
    if working.area > 0.0:
        try:
            candidate = _polylabel(working, tolerance=_tolerance(working))
        except Exception:  # degenerate input; fall through to fallbacks
            candidate = None
        if candidate is not None and _inside(reference, candidate):
            return Point(candidate.x, candidate.y)

    # 2. Centroid, if it happens to lie inside (cheap and often fine).
    centroid = working.centroid
    if _inside(reference, centroid):
        return Point(centroid.x, centroid.y)

    # 3. Shapely's guaranteed-interior point.
    for geom in (working, reference):
        try:
            rep = geom.representative_point()
        except Exception:
            continue
        if _inside(reference, rep):
            return Point(rep.x, rep.y)

    # 4. Zero-area / collapsed geometry: any vertex lies "on" the polygon.
    coords = list(reference.exterior.coords)
    if coords:
        x, y = coords[0][:2]
        return Point(x, y)

    raise ValueError("could not determine a label point for the given polygon")