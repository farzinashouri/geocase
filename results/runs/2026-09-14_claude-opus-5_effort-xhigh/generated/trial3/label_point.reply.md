```python
"""Label placement for polygons.

`label_point` picks a point at which a text label for a polygon can be drawn.
The returned point is always inside the polygon (not merely inside its bounding
box or convex hull), so labels never escape concave shapes, C-shapes, rings or
polygons with holes.

Strategy, in order:

1. The *pole of inaccessibility* -- the centre of the largest circle that fits
   inside the polygon.  This is the standard choice for label placement: it
   maximises the clear space around the label.  GEOS' ``maximum_inscribed_circle``
   is used when available, otherwise shapely's pure-Python ``polylabel``.
2. The centroid is preferred over the pole when it is inside the polygon *and*
   has nearly as much clearance, because for simple, roughly convex shapes the
   centroid reads as the more natural label anchor.
3. ``representative_point()`` as a guaranteed-inside last resort.

All computation is planar, in whatever coordinate system the polygon already
uses; nothing is reprojected and no CRS is assumed.  Tolerances are derived from
the polygon's own extent, so degrees, metres and feet all behave the same.  A
polygon spanning the antimeridian or a pole in geographic coordinates is treated
as the planar shape its coordinates describe.
"""

from __future__ import annotations

import math
from typing import Iterator

import shapely
from shapely.geometry import Point, Polygon
from shapely.ops import polylabel

__all__ = ["label_point"]

# Pole-of-inaccessibility search tolerance, as a fraction of the bounding-box
# diagonal.  Relative rather than absolute so the result is scale independent.
_RELATIVE_TOLERANCE = 1e-3

# Use the centroid instead of the pole when its clearance from the boundary is
# at least this fraction of the pole's clearance.
_CENTROID_PREFERENCE = 0.75


def label_point(polygon: Polygon) -> Point:
    """Return a point inside ``polygon`` suitable for anchoring a text label.

    Parameters
    ----------
    polygon:
        A shapely ``Polygon`` in any coordinate system.  Invalid polygons
        (self-intersecting rings and the like) are repaired first; the label is
        then placed inside the largest piece of the repaired shape.

    Returns
    -------
    Point
        A point guaranteed to lie in the polygon's interior.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely ``Polygon``.
    ValueError
        If the polygon is empty or has no interior to place a label in (zero
        area: a collapsed, linear or point-like polygon).
    """
    poly = _placeable_polygon(polygon)
    pole = _pole_of_inaccessibility(poly)

    if pole is None:
        # Documented by shapely as cheap and guaranteed to be within the
        # geometry, so this is the safety net rather than a preference.
        fallback = poly.representative_point()
        if not poly.contains(fallback):
            raise ValueError("could not place a label point inside the polygon")
        return fallback

    centroid = poly.centroid
    if poly.contains(centroid):
        boundary = poly.boundary
        if centroid.distance(boundary) >= _CENTROID_PREFERENCE * pole.distance(boundary):
            return centroid
    return pole


def _placeable_polygon(polygon: Polygon) -> Polygon:
    """Validate the input and return a polygon that actually has an interior."""
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        raise ValueError("cannot place a label point in an empty polygon")

    poly = polygon
    if not poly.is_valid:
        parts = sorted(_polygonal_parts(shapely.make_valid(poly)), key=lambda p: p.area)
        if not parts:
            raise ValueError("polygon has no valid polygonal area to label")
        poly = parts[-1]

    if poly.area == 0.0:
        raise ValueError("polygon has zero area, so no point lies inside it")
    return poly


def _polygonal_parts(geometry) -> Iterator[Polygon]:
    """Yield every non-empty Polygon in a geometry, descending into collections."""
    if isinstance(geometry, Polygon):
        if not geometry.is_empty:
            yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from _polygonal_parts(part)


def _pole_of_inaccessibility(poly: Polygon) -> Point | None:
    """Centre of the largest inscribed circle, or None if it cannot be found."""
    minx, miny, maxx, maxy = poly.bounds
    tolerance = math.hypot(maxx - minx, maxy - miny) * _RELATIVE_TOLERANCE

    # Both branches are optimisations over the representative_point() fallback,
    # and both depend on optional/underlying GEOS capabilities (shapely 2.1 and
    # GEOS >= 3.9 for the first), so failures are demoted to the next candidate
    # rather than raised.  Containment is re-checked because a point that is not
    # strictly inside would break this module's only hard guarantee.
    maximum_inscribed_circle = getattr(shapely, "maximum_inscribed_circle", None)
    if maximum_inscribed_circle is not None:
        try:
            radius_line = maximum_inscribed_circle(poly, tolerance=tolerance)
            candidate = Point(radius_line.coords[0])
        except Exception:
            candidate = None
        if candidate is not None and poly.contains(candidate):
            return candidate

    try:
        candidate = polylabel(poly, tolerance)
    except Exception:
        return None
    return candidate if poly.contains(candidate) else None
```