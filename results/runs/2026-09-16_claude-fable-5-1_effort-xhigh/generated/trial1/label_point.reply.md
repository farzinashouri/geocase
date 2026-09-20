```python
"""Label placement for polygons.

``label_point(polygon)`` returns a shapely ``Point`` that lies inside the given
polygon and is a good anchor for drawing a text label.  The preferred answer is
the polygon's pole of inaccessibility (the interior point farthest from the
boundary), which keeps labels away from edges and out of holes.  Every
candidate is verified against the input polygon, and progressively simpler
fallbacks are used so that an interior point is always returned.

The module is unit-agnostic: all search tolerances are derived from the
polygon's own extent, so it behaves the same for degrees, metres or feet.
Importing this module has no side effects.
"""

from __future__ import annotations

import math
from typing import Callable, Iterator, List, Optional

import shapely
from shapely.geometry import Point, Polygon
from shapely.geometry.base import BaseGeometry

try:
    from shapely.ops import polylabel as _polylabel
except Exception:  # pragma: no cover - very old shapely
    _polylabel = None

try:
    from shapely.validation import make_valid as _make_valid
except Exception:  # pragma: no cover - very old shapely
    _make_valid = None

__all__ = ["label_point"]

# Search precision expressed as a fraction of the polygon's narrower extent.
_RELATIVE_TOLERANCE = 0.01


def _polygons(geom: Optional[BaseGeometry]) -> Iterator[Polygon]:
    """Yield every non-empty Polygon found in ``geom``, recursing into collections."""
    if geom is None or geom.is_empty:
        return
    if isinstance(geom, Polygon):
        yield geom
        return
    for part in getattr(geom, "geoms", ()):
        yield from _polygons(part)


def _largest_polygon(geom: Optional[BaseGeometry]) -> Optional[Polygon]:
    """Return the largest-area Polygon contained in ``geom``, or None."""
    best: Optional[Polygon] = None
    best_area = -1.0
    for poly in _polygons(geom):
        area = poly.area
        if area > best_area:
            best, best_area = poly, area
    return best


def _cleaned(polygon: BaseGeometry) -> Optional[Polygon]:
    """Return a valid Polygon representing (the largest piece of) ``polygon``."""
    geom: Optional[BaseGeometry] = polygon
    if not polygon.is_valid:
        fixed: Optional[BaseGeometry] = None
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
        if fixed is not None and not fixed.is_empty:
            geom = fixed
    return _largest_polygon(geom)


def _tolerance(polygon: Polygon) -> float:
    """Search precision scaled to the polygon's extent (0.0 if degenerate)."""
    minx, miny, maxx, maxy = polygon.bounds
    span = min(maxx - minx, maxy - miny)
    if not (math.isfinite(span) and span > 0.0):
        return 0.0
    return span * _RELATIVE_TOLERANCE


def _contains(geom: BaseGeometry, point: Point) -> bool:
    try:
        return bool(geom.contains(point))
    except Exception:
        return False


def _inscribed_circle_center(polygon: Polygon, tolerance: float) -> Optional[Point]:
    """Pole of inaccessibility via GEOS MaximumInscribedCircle (shapely >= 2.1)."""
    fn = getattr(shapely, "maximum_inscribed_circle", None)
    if fn is None or tolerance <= 0.0:
        return None
    try:
        radius_line = fn(polygon, tolerance)
        if radius_line is None or radius_line.is_empty:
            return None
        x, y = radius_line.coords[0][:2]
    except Exception:
        return None
    return Point(x, y)


def _pole_of_inaccessibility(polygon: Polygon, tolerance: float) -> Optional[Point]:
    """Pole of inaccessibility via shapely's pure-Python polylabel."""
    if _polylabel is None or tolerance <= 0.0:
        return None
    try:
        return _polylabel(polygon, tolerance=tolerance)
    except Exception:
        return None


def label_point(polygon: BaseGeometry) -> Point:
    """Return a shapely ``Point`` inside ``polygon`` suitable for anchoring a label.

    Parameters
    ----------
    polygon:
        A shapely ``Polygon`` in any coordinate system.  A ``MultiPolygon`` (or
        a collection containing polygons) is also accepted; the label is placed
        in its largest part.  Invalid polygons are repaired internally before
        searching, but the result is still checked against the original input.

    Returns
    -------
    shapely.geometry.Point
        A 2-D point that lies inside the polygon.  Where possible this is the
        pole of inaccessibility (the interior point farthest from any edge or
        hole); otherwise a guaranteed interior point is returned.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely geometry.
    ValueError
        If ``polygon`` is empty.
    """
    if not isinstance(polygon, BaseGeometry):
        raise TypeError(
            "label_point() expects a shapely geometry, got %r" % type(polygon).__name__
        )
    if polygon.is_empty:
        raise ValueError("cannot place a label inside an empty geometry")

    clean = _cleaned(polygon)

    # Containment is checked against the input first.  If the input is invalid
    # (where GEOS predicates are unreliable) the repaired version is also accepted.
    targets: List[BaseGeometry] = [polygon]
    if clean is not None and clean is not polygon and not polygon.is_valid:
        targets.append(clean)

    candidates: List[Callable[[], Optional[Point]]] = []
    if clean is not None:
        tol = _tolerance(clean)
        candidates.append(lambda: _inscribed_circle_center(clean, tol))
        candidates.append(lambda: _pole_of_inaccessibility(clean, tol))
        candidates.append(clean.representative_point)
    candidates.append(polygon.representative_point)
    candidates.append(lambda: polygon.centroid)

    for make in candidates:
        try:
            pt = make()
        except Exception:
            continue
        if not isinstance(pt, Point) or pt.is_empty:
            continue
        if any(_contains(target, pt) for target in targets):
            return Point(pt.x, pt.y)

    # Last resort (e.g. zero-area polygons with no interior): GEOS guarantees
    # representative_point() lies on the geometry itself.
    try:
        pt = polygon.representative_point()
    except Exception:
        pt = polygon.centroid
    return Point(pt.x, pt.y)
```