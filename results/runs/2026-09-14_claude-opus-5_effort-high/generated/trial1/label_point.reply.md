```python
"""Compute a point inside a polygon at which its label can be drawn.

``label_point`` returns the polygon's *pole of inaccessibility*: the interior
point that is farthest away from the polygon's boundary (including the
boundaries of any holes).  That is the point with the most room around it, so
it is where a text label should be anchored.  Unlike the centroid it is always
inside the polygon, and unlike ``Polygon.representative_point`` it is not
biased towards the boundary of concave, crescent or C-shaped polygons.

The search is a vectorised variant of Mapbox's ``polylabel``: a quadtree over
the bounding box, explored best-first by an upper bound on the clearance
achievable within each cell.  Among cells whose clearance is equal (within
tolerance) the one closest to the centroid wins, so symmetric shapes such as
rectangles get the label in the middle rather than at an arbitrary point of
their medial axis.

Coordinates are treated as planar and nothing here depends on their units, so
the "inside the polygon" guarantee holds for any coordinate system.  For
geographic coordinates the clearance is maximised in degree space, which is
fine for label placement but is not a geodesic distance.
"""

from __future__ import annotations

import itertools
import heapq
import math

import numpy as np
import shapely
from shapely.geometry import Point, Polygon
from shapely.geometry.base import BaseGeometry

__all__ = ["label_point"]

_SQRT2 = math.sqrt(2.0)

# The quadtree stops subdividing once no cell can improve the clearance by more
# than this fraction of the bounding-box diagonal.  It is relative, which keeps
# the search independent of the coordinate system's units.
_RELATIVE_TOLERANCE = 1e-4

# Safety net against pathological geometries; the tolerance above normally
# terminates the search after far fewer cells than this.
_MAX_CELLS = 20000


def label_point(polygon: Polygon) -> Point:
    """Return a ``Point`` inside ``polygon`` suitable for anchoring a label.

    Parameters
    ----------
    polygon
        A shapely ``Polygon`` in any coordinate system.  Invalid polygons are
        repaired first, and a ``MultiPolygon`` is accepted as a convenience
        (its largest part is labelled).

    Returns
    -------
    Point
        A point that lies strictly inside the polygon.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely geometry.
    ValueError
        If the polygon is empty, has non-finite coordinates, or encloses no
        area -- in those cases no interior point exists.
    """
    poly = _as_polygon(polygon)

    candidate = _polylabel(poly)
    if candidate is not None and _contains(poly, candidate):
        return candidate

    # Slivers so thin that no sampled cell centre landed inside: fall back to
    # GEOS, which guarantees a point on (and for a valid, positive-area
    # polygon, inside) the surface.
    fallback = poly.point_on_surface()
    if _contains(poly, fallback):
        return fallback

    raise ValueError("could not find a point inside the polygon")


def _as_polygon(geometry: BaseGeometry) -> Polygon:
    """Validate the input and return a valid, positive-area ``Polygon``."""
    if not isinstance(geometry, BaseGeometry):
        raise TypeError(
            f"expected a shapely Polygon, got {type(geometry).__name__}"
        )
    if geometry.is_empty:
        raise ValueError("cannot label an empty polygon")
    if not np.all(np.isfinite(geometry.bounds)):
        raise ValueError("polygon has non-finite coordinates")

    poly = geometry
    if not isinstance(poly, Polygon) or not poly.is_valid:
        poly = _largest_polygon(shapely.make_valid(geometry))

    if poly is None or poly.is_empty or poly.area <= 0.0:
        raise ValueError("polygon encloses no area, so it has no interior point")
    return poly


def _largest_polygon(geometry: BaseGeometry):
    """Return the biggest ``Polygon`` inside ``geometry``, or ``None``."""
    parts = [
        part
        for part in _flatten(geometry)
        if isinstance(part, Polygon) and not part.is_empty
    ]
    if not parts:
        return None
    return max(parts, key=lambda part: part.area)


def _flatten(geometry: BaseGeometry):
    """Yield the single-part geometries of a possibly nested collection."""
    parts = getattr(geometry, "geoms", None)
    if parts is None:
        yield geometry
        return
    for part in parts:
        yield from _flatten(part)


def _contains(polygon: Polygon, point: Point) -> bool:
    return bool(shapely.contains_xy(polygon, point.x, point.y))


def _polylabel(polygon: Polygon):
    """Best-first quadtree search for the pole of inaccessibility."""
    minx, miny, maxx, maxy = polygon.bounds
    width = maxx - minx
    height = maxy - miny
    if width <= 0.0 or height <= 0.0:
        return None

    boundary = polygon.boundary
    centroid = polygon.centroid
    cx, cy = centroid.x, centroid.y
    tolerance = math.hypot(width, height) * _RELATIVE_TOLERANCE

    # Seed with a regular grid of square cells covering the bounding box, plus
    # the centroid as a zero-sized cell so it can win ties outright.
    cell_size = min(width, height)
    half = cell_size / 2.0
    xs = np.arange(minx + half, maxx, cell_size)
    ys = np.arange(miny + half, maxy, cell_size)
    if xs.size == 0:
        xs = np.array([minx + width / 2.0])
    if ys.size == 0:
        ys = np.array([miny + height / 2.0])
    grid_x, grid_y = np.meshgrid(xs, ys)

    seeds = _cells(grid_x.ravel(), grid_y.ravel(), half, polygon, boundary, cx, cy)
    seeds += _cells([cx], [cy], 0.0, polygon, boundary, cx, cy)

    queue = []
    counter = itertools.count()
    state = {"best": None, "max_clearance": -math.inf}

    def consider(cell):
        clearance = cell[3]
        if clearance > state["max_clearance"]:
            state["max_clearance"] = clearance
        if clearance <= 0.0:  # cell centre is outside the polygon
            return
        best = state["best"]
        if best is None or _is_better(cell, best, tolerance):
            state["best"] = cell

    for cell in seeds:
        consider(cell)
        heapq.heappush(queue, (-cell[4], next(counter), cell))

    processed = 0
    while queue and processed < _MAX_CELLS:
        _, _, cell = heapq.heappop(queue)
        processed += 1
        x, y, cell_half, _, reach, _ = cell
        # No point in this cell can beat what we already have.
        if reach - state["max_clearance"] <= tolerance:
            continue
        child_half = cell_half / 2.0
        child_x = (x - child_half, x + child_half, x - child_half, x + child_half)
        child_y = (y - child_half, y - child_half, y + child_half, y + child_half)
        for child in _cells(child_x, child_y, child_half, polygon, boundary, cx, cy):
            consider(child)
            heapq.heappush(queue, (-child[4], next(counter), child))

    best = state["best"]
    if best is None:
        return None
    return Point(best[0], best[1])


def _cells(xs, ys, half, polygon, boundary, cx, cy):
    """Build cell tuples ``(x, y, half, clearance, reach, centroid_distance)``.

    ``clearance`` is the distance from the cell centre to the polygon
    boundary, negated when the centre falls outside the polygon.  ``reach`` is
    the largest clearance any point of the cell could have, i.e. the priority
    used to order the search.
    """
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    points = shapely.points(xs, ys)
    distance = shapely.distance(boundary, points)
    inside = shapely.contains_xy(polygon, xs, ys)
    clearance = np.where(inside, distance, -distance)
    reach = clearance + half * _SQRT2
    centroid_distance = np.hypot(xs - cx, ys - cy)
    return [
        (float(x), float(y), half, float(c), float(r), float(d))
        for x, y, c, r, d in zip(xs, ys, clearance, reach, centroid_distance)
    ]


def _is_better(cell, best, tolerance) -> bool:
    """Prefer more clearance; break near-ties by closeness to the centroid."""
    if cell[3] > best[3] + tolerance:
        return True
    if cell[3] < best[3] - tolerance:
        return False
    return cell[5] < best[5]
```