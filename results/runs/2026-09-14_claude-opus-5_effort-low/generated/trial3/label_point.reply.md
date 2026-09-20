```python
"""Compute a point inside a polygon suitable for drawing a text label.

The main entry point is :func:`label_point`, which returns the "pole of
inaccessibility" of a polygon: the interior point furthest from the
boundary.  That point is a better anchor for a label than the centroid,
which can fall outside concave or ring-shaped polygons.

The algorithm is Vladimir Agafonkin's polylabel: subdivide the polygon's
bounding box into cells and explore them best-first, keeping the cell
whose potential (distance to boundary plus the cell's half-diagonal)
could still beat the best point found so far.

The module is coordinate-system agnostic; all arithmetic is planar and in
the units of the input geometry.
"""

from __future__ import annotations

import heapq
import itertools
import math

from shapely.geometry import Point, Polygon
from shapely.geometry.base import BaseGeometry

__all__ = ["label_point"]

# Stop subdividing once a cell can only improve the result by this
# fraction of the polygon's size.  1e-3 is well below label-placement
# precision while keeping the search short.
_RELATIVE_PRECISION = 1e-3

_SQRT2 = math.sqrt(2.0)


def label_point(polygon: Polygon) -> Point:
    """Return a :class:`~shapely.geometry.Point` inside ``polygon``.

    Parameters
    ----------
    polygon:
        A shapely ``Polygon`` in any coordinate reference system.

    Returns
    -------
    Point
        A point guaranteed to lie within ``polygon``, chosen to be far
        from the boundary so a label drawn there stays legible.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely ``Polygon``.
    ValueError
        If ``polygon`` is empty or has no interior area.
    """
    if not isinstance(polygon, BaseGeometry) or polygon.geom_type != "Polygon":
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        raise ValueError("cannot label an empty polygon")

    # Invalid rings (self-intersections, bad winding) break the
    # point-in-polygon predicate, so repair before measuring anything.
    work = polygon if polygon.is_valid else _largest_polygon(polygon.buffer(0))
    if work is None or work.is_empty or work.area <= 0.0:
        raise ValueError("polygon has no interior area to place a label in")

    best = _pole_of_inaccessibility(work)

    # The search returns a cell centre, which is interior by construction,
    # but degenerate geometries can still slip through; fall back to
    # shapely's guaranteed-interior point rather than returning garbage.
    if not work.covers(best):
        best = work.representative_point()
    return best


def _largest_polygon(geometry: BaseGeometry) -> Polygon | None:
    """Return the biggest ``Polygon`` part of ``geometry``, if any."""
    if geometry.is_empty:
        return None
    if geometry.geom_type == "Polygon":
        return geometry
    parts = [g for g in getattr(geometry, "geoms", ()) if g.geom_type == "Polygon"]
    if not parts:
        return None
    return max(parts, key=lambda g: g.area)


def _pole_of_inaccessibility(polygon: Polygon) -> Point:
    """Best-first search for the interior point furthest from the boundary."""
    min_x, min_y, max_x, max_y = polygon.bounds
    width = max_x - min_x
    height = max_y - min_y
    cell_size = min(width, height)

    # A zero-width or zero-height bounding box means a degenerate polygon.
    if cell_size <= 0.0:
        return polygon.representative_point()

    boundary = polygon.boundary
    precision = _RELATIVE_PRECISION * max(width, height)

    # Ties in the priority queue are broken by an ever-increasing counter
    # so heapq never has to compare Points.
    counter = itertools.count()
    queue: list[tuple[float, int, float, float, float]] = []

    def push(x: float, y: float, half: float) -> tuple[float, float, float]:
        distance = _signed_distance(x, y, polygon, boundary)
        potential = distance + half * _SQRT2
        heapq.heappush(queue, (-potential, next(counter), x, y, half))
        return distance, x, y

    # Seed with a grid covering the bounding box.
    half = cell_size / 2.0
    x = min_x + half
    while x < max_x:
        y = min_y + half
        while y < max_y:
            push(x, y, half)
            y += cell_size
        x += cell_size

    # Seed the best guess with the centroid-derived cell, which is often
    # already optimal for convex shapes.
    best = _centroid_cell(polygon)
    best_distance = _signed_distance(best[0], best[1], polygon, boundary)

    bbox_centre = push((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, half)
    if bbox_centre[0] > best_distance:
        best_distance, best = bbox_centre[0], (bbox_centre[1], bbox_centre[2])

    while queue:
        neg_potential, _, cx, cy, half = heapq.heappop(queue)
        potential = -neg_potential

        # Every remaining cell has a lower ceiling than this one, so if
        # this cell cannot beat the incumbent, none of them can.
        if potential - best_distance <= precision:
            break

        child_half = half / 2.0
        for dx, dy in ((-child_half, -child_half), (child_half, -child_half),
                       (-child_half, child_half), (child_half, child_half)):
            distance, px, py = push(cx + dx, cy + dy, child_half)
            if distance > best_distance:
                best_distance, best = distance, (px, py)

    return Point(best)


def _centroid_cell(polygon: Polygon) -> tuple[float, float]:
    """Return centroid coordinates, or a representative point if unusable."""
    centroid = polygon.centroid
    if centroid.is_empty:
        point = polygon.representative_point()
        return point.x, point.y
    return centroid.x, centroid.y


def _signed_distance(x: float, y: float, polygon: Polygon, boundary: BaseGeometry) -> float:
    """Distance from ``(x, y)`` to the boundary, negative outside the polygon."""
    point = Point(x, y)
    distance = point.distance(boundary)
    return distance if polygon.contains(point) else -distance
```