```python
"""Label placement for polygons.

``label_point`` returns a polygon's *pole of inaccessibility*: the interior
point that is farthest from the boundary. That is where a text label sits most
comfortably -- unlike the centroid, it is always inside the polygon, and unlike
``Polygon.representative_point()`` it does not hug a boundary or a hole.

The search is the branch-and-bound quadtree refinement popularised by Mapbox's
polylabel, done here with shapely's own distance/containment predicates so that
holes are handled for free.

Coordinates are treated as planar. For geographic (lon/lat) input the metric is
degrees, which is fine for choosing a label anchor but is not a true distance;
polygons crossing the antimeridian or covering a pole are out of scope.
"""

from __future__ import annotations

import heapq
import math
from itertools import count

import numpy as np
import shapely
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry

__all__ = ["label_point"]

_SQRT2 = math.sqrt(2.0)

# Stopping precision, as a fraction of the longest bounding-box side. Keeping it
# relative is what makes the function coordinate-system agnostic: the input may
# be in degrees, metres or US survey feet, and an absolute tolerance that is
# sensible in one is meaningless in the others.
_PRECISION = 1e-4

_MAX_INITIAL_CELLS = 4096
_MAX_SUBDIVISIONS = 20_000


def label_point(polygon, *, precision: float = _PRECISION) -> Point:
    """Return a ``Point`` inside ``polygon`` at which to draw its label.

    Parameters
    ----------
    polygon:
        A shapely ``Polygon`` in any coordinate system. ``MultiPolygon`` and
        ``GeometryCollection`` inputs are accepted as a convenience; the
        largest polygonal part is labelled. Invalid input is repaired with
        ``make_valid`` before labelling.
    precision:
        Search tolerance as a fraction of the polygon's longest bounding-box
        side. Smaller values centre the point more precisely at the cost of
        more iterations.

    Returns
    -------
    Point
        A point guaranteed to satisfy ``polygon.contains(point)``.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely geometry.
    ValueError
        If the geometry is empty, non-finite, or has no positive-area part --
        such a geometry has no interior, so no interior point exists.
    """
    poly = _largest_polygon(polygon)
    minx, miny, maxx, maxy = poly.bounds
    width, height = maxx - minx, maxy - miny

    boundary = poly.boundary
    shapely.prepare(poly)  # caches a prepared geometry for the contains tests

    # Seed with a point GEOS guarantees to be in the interior. Every candidate
    # below only replaces it if it is strictly farther from the boundary, so
    # the result is inside the polygon no matter how the search is truncated.
    seed = poly.representative_point()
    best_x, best_y = seed.x, seed.y
    best_d = float(_signed_distance(poly, boundary, [best_x], [best_y])[0])

    tolerance = max(width, height) * float(precision)

    # Cover the bounding box with square cells. Squares of side min(width,
    # height) are the natural choice, but cap their number so that a long thin
    # sliver does not seed millions of cells; any cover works, because each
    # cell's upper bound accounts for its own size.
    cell = min(width, height)
    if (width / cell) * (height / cell) > _MAX_INITIAL_CELLS:
        cell = math.sqrt(width * height / _MAX_INITIAL_CELLS)
    half = cell / 2.0

    grid_x, grid_y = np.meshgrid(
        np.arange(minx + half, maxx + half, cell),
        np.arange(miny + half, maxy + half, cell),
    )
    grid_x, grid_y = grid_x.ravel(), grid_y.ravel()
    distances = _signed_distance(poly, boundary, grid_x, grid_y)

    tiebreak = count()
    queue: list[tuple[float, int, float, float, float]] = []
    for x, y, d in zip(grid_x, grid_y, distances):
        if d > best_d:
            best_x, best_y, best_d = float(x), float(y), float(d)
        # A cell cannot beat the distance at its centre by more than its
        # half-diagonal, which makes this an admissible upper bound.
        upper = float(d) + half * _SQRT2
        if upper - best_d > tolerance:
            heapq.heappush(queue, (-upper, next(tiebreak), float(x), float(y), half))

    for _ in range(_MAX_SUBDIVISIONS):
        if not queue:
            break
        neg_upper, _, x, y, h = heapq.heappop(queue)
        # Best-first: if the most promising cell cannot improve on the incumbent
        # by more than the tolerance, neither can anything still queued.
        if -neg_upper - best_d <= tolerance:
            break

        quarter = h / 2.0
        child_x = np.array([x - quarter, x + quarter, x - quarter, x + quarter])
        child_y = np.array([y - quarter, y - quarter, y + quarter, y + quarter])
        child_d = _signed_distance(poly, boundary, child_x, child_y)

        for cx, cy, cd in zip(child_x, child_y, child_d):
            cd = float(cd)
            if cd > best_d:
                best_x, best_y, best_d = float(cx), float(cy), cd
            upper = cd + quarter * _SQRT2
            if upper - best_d > tolerance:
                heapq.heappush(
                    queue, (-upper, next(tiebreak), float(cx), float(cy), quarter)
                )

    point = Point(best_x, best_y)
    if not poly.contains(point):
        # Only reachable for slivers where the inscribed radius is at the limit
        # of floating-point resolution; fall back to the guaranteed-inside seed.
        point = seed
    return point


def _signed_distance(polygon, boundary, xs, ys) -> np.ndarray:
    """Distance from each (x, y) to the boundary, negated outside the polygon.

    Using the polygon's full boundary means interior rings repel candidates
    just like the exterior does, so labels never land in a hole.
    """
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    points = shapely.points(xs, ys)
    distance = shapely.distance(points, boundary)
    inside = shapely.contains(polygon, points)
    return np.where(inside, distance, -distance)


def _largest_polygon(geometry):
    """Validate the input and reduce it to a single positive-area polygon."""
    if not isinstance(geometry, BaseGeometry):
        raise TypeError(f"expected a shapely geometry, got {type(geometry).__name__}")
    if geometry.is_empty:
        raise ValueError("cannot label an empty geometry")
    if not all(math.isfinite(bound) for bound in geometry.bounds):
        raise ValueError("geometry has non-finite coordinates")

    candidate = geometry if geometry.is_valid else shapely.make_valid(geometry)
    parts = [part for part in _polygonal_parts(candidate) if part.area > 0.0]
    if not parts:
        raise ValueError(
            "geometry has no positive-area polygonal part, so it has no interior"
        )
    return max(parts, key=lambda part: part.area)


def _polygonal_parts(geometry) -> list:
    """Flatten a geometry to its (possibly nested) polygon components."""
    kind = geometry.geom_type
    if kind == "Polygon":
        return [] if geometry.is_empty else [geometry]
    if kind in ("MultiPolygon", "GeometryCollection"):
        parts: list = []
        for part in geometry.geoms:
            parts.extend(_polygonal_parts(part))
        return parts
    return []
```