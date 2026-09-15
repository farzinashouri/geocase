```python
"""Compute a point inside a polygon suitable for drawing a text label.

The returned point is the *pole of inaccessibility*: the interior point that is
farthest from the polygon boundary.  For labelling this is a much better choice
than the centroid, which can fall outside concave or multi-part shapes, and
better than :meth:`shapely.Polygon.representative_point`, which only guarantees
containment and often lands very close to an edge.

The module is coordinate-system agnostic: all tolerances are derived from the
size of the input geometry, so it behaves identically for degrees, metres or
feet.  Importing it has no side effects.
"""

from __future__ import annotations

import math

import shapely
from shapely.geometry import Point, Polygon
from shapely.ops import polylabel

__all__ = ["label_point"]

# Fraction of the geometry's diagonal used as the search tolerance.  Small
# enough that the label sits visually at the widest part of the shape, large
# enough that the search terminates quickly on complex polygons.
_TOLERANCE_RATIO = 1e-3


def label_point(polygon: Polygon) -> Point:
    """Return a :class:`~shapely.geometry.Point` inside ``polygon``.

    Parameters
    ----------
    polygon:
        A shapely ``Polygon`` in any coordinate reference system.  Polygons
        with holes are supported; the returned point never falls in a hole.
        Self-intersecting (invalid) polygons are repaired before use.

    Returns
    -------
    Point
        A point guaranteed to lie in the interior of ``polygon``, positioned
        away from the boundary so that a label drawn there stays legible.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely ``Polygon``.
    ValueError
        If ``polygon`` is empty, or is degenerate (zero area) and therefore has
        no interior to place a label in.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        raise ValueError("cannot label an empty polygon")

    target = _repair(polygon)
    tolerance = _tolerance(target)

    for candidate in _candidates(target, tolerance):
        if candidate is not None and not candidate.is_empty and target.contains(candidate):
            return candidate

    # `representative_point` is documented to be inside the polygon, so we only
    # get here for geometries that are pathological beyond repair.
    raise ValueError("could not find an interior point for the given polygon")


def _repair(polygon: Polygon) -> Polygon:
    """Return a valid, non-degenerate ``Polygon`` equivalent to ``polygon``."""
    valid = polygon if polygon.is_valid else shapely.make_valid(polygon)

    # `make_valid` may return a collection (e.g. a polygon plus the dangling
    # lines of a bow-tie).  Label the largest polygonal part: that is the piece
    # a reader would consider "the" shape.
    parts = [
        part
        for part in shapely.get_parts(shapely.geometry.GeometryCollection([valid]))
        if isinstance(part, Polygon) and not part.is_empty and part.area > 0
    ]
    if not parts:
        raise ValueError("polygon has zero area; there is no interior to label")
    return max(parts, key=lambda part: part.area)


def _tolerance(polygon: Polygon) -> float:
    """Pick a search tolerance proportional to the polygon's own extent."""
    min_x, min_y, max_x, max_y = polygon.bounds
    diagonal = math.hypot(max_x - min_x, max_y - min_y)
    tolerance = diagonal * _TOLERANCE_RATIO
    if not math.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("polygon bounds are degenerate or non-finite")
    return tolerance


def _candidates(polygon: Polygon, tolerance: float):
    """Yield interior-point candidates, best first."""
    yield _maximum_inscribed_circle_center(polygon, tolerance)
    yield _polylabel_center(polygon, tolerance)
    yield polygon.representative_point()


def _maximum_inscribed_circle_center(polygon: Polygon, tolerance: float):
    """Exact pole of inaccessibility via GEOS, if this build provides it."""
    maximum_inscribed_circle = getattr(shapely, "maximum_inscribed_circle", None)
    if maximum_inscribed_circle is None:  # older GEOS/shapely
        return None
    try:
        radius_line = maximum_inscribed_circle(polygon, tolerance=tolerance)
    except Exception:  # unsupported GEOS version, or a geometry GEOS rejects
        return None
    if radius_line is None or radius_line.is_empty:
        return None
    # The line runs from the circle centre to its nearest boundary point.
    center_x, center_y = radius_line.coords[0]
    return Point(center_x, center_y)


def _polylabel_center(polygon: Polygon, tolerance: float):
    """Shapely's pure-Python pole-of-inaccessibility approximation."""
    try:
        return polylabel(polygon, tolerance=tolerance)
    except Exception:
        return None
```