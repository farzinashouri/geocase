"""Label placement for polygons.

``label_point`` returns a polygon's *pole of inaccessibility*: the interior
point furthest from the boundary.  That is the point a cartographer wants for a
text label -- unlike the centroid it is always inside the polygon, and unlike
``representative_point()`` it sits in the widest part of the shape rather than
wherever a scan line happens to land.

The search is the standard quad-tree refinement (Mapbox's "polylabel"): cover
the bounding box with square cells, then repeatedly split the most promising
cell, where a cell's potential is its centre's distance to the boundary plus the
half-diagonal.  Cells that cannot beat the best point found so far are pruned.

Everything is planar, so the polygon may be in any coordinate system; the
returned point uses the input's coordinates untouched.  For geographic
coordinates the result is the pole of inaccessibility in degree space, which is
what you want for labelling a map drawn in those same coordinates.
"""

from __future__ import annotations

import heapq
import itertools
import math

import numpy as np
import shapely
from shapely.geometry import Point, Polygon

__all__ = ["label_point"]

_SQRT2 = math.sqrt(2.0)


def label_point(polygon, *, precision=None, max_iterations=10_000):
    """Return a ``Point`` inside ``polygon`` at which to draw its label.

    Parameters
    ----------
    polygon:
        A shapely ``Polygon``, in any coordinate system.  Holes are honoured:
        the label point never lands in one.  Invalid (e.g. self-intersecting)
        input is repaired first, and the largest resulting piece is labelled.
    precision:
        Stop refining once the label point cannot be improved by more than this
        distance.  Defaults to 1/1000 of the polygon's longest bounding-box
        side, which keeps the function scale- and unit-agnostic.
    max_iterations:
        Safety valve on the number of cells examined.  The search normally
        converges well before this; if it is hit, the best point found so far is
        returned (still inside the polygon).

    Returns
    -------
    Point
        A point strictly inside ``polygon``.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely ``Polygon``.
    ValueError
        If the polygon is empty or has zero area, in which case it has no
        interior and no such point exists.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        raise ValueError("cannot label an empty polygon")

    working = _as_valid_polygon(polygon)
    minx, miny, maxx, maxy = working.bounds
    width = maxx - minx
    height = maxy - miny
    if width <= 0.0 or height <= 0.0 or working.area <= 0.0:
        raise ValueError("polygon has zero area, so it contains no interior point")

    if precision is None:
        precision = max(width, height) / 1000.0
    else:
        precision = float(precision)
        if precision <= 0.0:
            raise ValueError("precision must be positive")

    max_iterations = int(max_iterations)
    if max_iterations <= 0:
        raise ValueError("max_iterations must be positive")

    x, y, distance = _pole_of_inaccessibility(working, precision, max_iterations)
    if distance > 0.0:
        return Point(x, y)

    # A sliver thin enough that no cell centre landed inside it.  This point is
    # not the nicest place for a label, but it is guaranteed to be inside.
    return working.representative_point()


def _as_valid_polygon(polygon):
    """Return ``polygon`` itself, or the largest polygonal piece of its repair."""
    if polygon.is_valid:
        return polygon

    parts = _polygonal_parts(shapely.make_valid(polygon))
    if not parts:
        raise ValueError("polygon is invalid and repairing it leaves no area")
    return max(parts, key=lambda part: part.area)


def _polygonal_parts(geometry):
    """Flatten a geometry to its non-empty ``Polygon`` components."""
    if geometry.is_empty:
        return []
    if isinstance(geometry, Polygon):
        return [geometry]
    if hasattr(geometry, "geoms"):
        return [part for child in geometry.geoms for part in _polygonal_parts(child)]
    return []


def _pole_of_inaccessibility(polygon, precision, max_iterations):
    """Return ``(x, y, signed_distance)`` for the polygon's interior pole."""
    boundary = polygon.boundary
    # Only attaches GEOS's spatial-index cache to the geometry; the shape and
    # every predicate result are unchanged.
    shapely.prepare(polygon)

    minx, miny, maxx, maxy = polygon.bounds
    cell_size = min(maxx - minx, maxy - miny)
    half = cell_size / 2.0

    # Seed with a regular grid of square cells over the bounding box, plus the
    # centroid, which is already the answer for anything convex-ish.
    grid_x, grid_y = np.meshgrid(
        np.arange(minx + half, maxx, cell_size),
        np.arange(miny + half, maxy, cell_size),
    )
    centroid = polygon.centroid
    xs = np.append(grid_x.ravel(), centroid.x)
    ys = np.append(grid_y.ravel(), centroid.y)
    ds = _signed_distances(polygon, boundary, xs, ys)

    counter = itertools.count()  # tie-breaker so heapq never compares floats twice
    queue = []
    for x, y, d in zip(xs[:-1], ys[:-1], ds[:-1]):
        heapq.heappush(
            queue, (-(d + half * _SQRT2), next(counter), float(x), float(y), half, float(d))
        )

    best = (float(xs[-1]), float(ys[-1]), float(ds[-1]))

    for _ in range(max_iterations):
        if not queue:
            break
        negated_potential, _, x, y, size, d = heapq.heappop(queue)
        if d > best[2]:
            best = (x, y, d)
        # The heap is ordered by potential, so once the best remaining cell
        # cannot improve on the incumbent, none of them can.
        if -negated_potential - best[2] <= precision:
            break

        size /= 2.0
        child_x = np.array([x - size, x + size, x - size, x + size])
        child_y = np.array([y - size, y - size, y + size, y + size])
        child_d = _signed_distances(polygon, boundary, child_x, child_y)
        for cx, cy, cd in zip(child_x, child_y, child_d):
            heapq.heappush(
                queue,
                (-(cd + size * _SQRT2), next(counter), float(cx), float(cy), size, float(cd)),
            )

    return best


def _signed_distances(polygon, boundary, xs, ys):
    """Distance from each ``(x, y)`` to the boundary, negated outside the polygon."""
    points = shapely.points(np.asarray(xs, dtype=float), np.asarray(ys, dtype=float))
    distances = shapely.distance(points, boundary)
    inside = shapely.contains(polygon, points)
    return np.where(inside, distances, -distances)