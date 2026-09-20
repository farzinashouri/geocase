```python
"""Label-point placement for polygons.

``label_point`` returns a polygon's *pole of inaccessibility*: the interior
point that is furthest from the boundary.  That is where a text label sits
most comfortably.  Unlike the centroid it is guaranteed to fall inside the
polygon (centroids of C-shaped or horseshoe polygons fall outside), and
unlike ``Polygon.representative_point`` it stays well clear of edges and
holes, so the label has room around it.

The search is the usual quadtree refinement (Agafonkin's polylabel) with two
deliberate differences from ``shapely.ops.polylabel``:

* distances are measured to the polygon's *full* boundary, so interior rings
  push the label away exactly like the outer ring does;
* the stopping tolerance is derived from the polygon's own extent rather than
  being an absolute number, so results are identical whether the geometry is
  in degrees, feet or metres.

Importing this module has no side effects.
"""

from __future__ import annotations

import heapq
import itertools
import math
from typing import Iterator, Optional, Tuple

from shapely.geometry import Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.prepared import prep
from shapely.validation import make_valid

__all__ = ["label_point"]

# Diagonal half-length factor: the furthest a point in a square cell of
# half-size h can be from the cell centre.
_SQRT2 = math.sqrt(2.0)

# Stop refining once cells can only improve on the best distance found by this
# fraction of the polygon's longest side.  1/1000 is far below any plausible
# label-rendering precision while keeping the search short.
_DEFAULT_PRECISION = 1.0e-3

# Seed grid is capped along the long axis so that extremely elongated polygons
# (a river buffer, say) do not generate a huge number of starting cells.  The
# refinement step recovers any accuracy lost to the coarser seeding.
_MAX_SEED_CELLS = 64

# Hard bound on refinement steps; the best-so-far point is always valid, so
# hitting this cap degrades precision rather than correctness.
_MAX_ITERATIONS = 100_000

# A cell in the search: (upper_bound, distance, x, y, half_size).
_Cell = Tuple[float, float, float, float, float]


def label_point(polygon: Polygon, *, precision: float = _DEFAULT_PRECISION) -> Point:
    """Return a point inside ``polygon`` suitable for drawing a label at.

    Parameters
    ----------
    polygon:
        A shapely :class:`~shapely.geometry.Polygon` in any coordinate system.
        Invalid polygons (self-intersections, bowties) are repaired first and
        the largest resulting piece is labelled.
    precision:
        Search tolerance as a fraction of the polygon's longest bounding-box
        side.  Smaller values cost more time and buy a slightly better centred
        point; the default is already well below display precision.

    Returns
    -------
    Point
        A point that lies strictly inside the polygon.

    Raises
    ------
    TypeError
        If ``polygon`` is not a shapely ``Polygon``.
    ValueError
        If ``polygon`` is empty or encloses no area (a line, a point, or a
        collapsed sliver), since such a shape has no interior to label, or if
        ``precision`` is not positive.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if not precision > 0.0:
        raise ValueError(f"precision must be positive, got {precision!r}")
    if polygon.is_empty:
        raise ValueError("cannot label an empty polygon")

    working = polygon if polygon.is_valid else _largest_polygon(make_valid(polygon))
    if working is None or working.is_empty or working.area <= 0.0:
        raise ValueError("polygon encloses no area, so it has no interior point")

    contains = prep(working).contains
    boundary = working.boundary

    minx, miny, maxx, maxy = working.bounds
    long_side = max(maxx - minx, maxy - miny)
    tolerance = long_side * precision

    best = _search(working, boundary, contains, tolerance)
    if best is not None:
        return best

    # Unreachable for any polygon with area, but a guaranteed-interior point
    # is cheap insurance against a pathological geometry defeating the search.
    fallback = working.representative_point()
    if contains(fallback):
        return fallback
    raise ValueError("could not place a label point inside the polygon")


def _search(
    polygon: Polygon,
    boundary: BaseGeometry,
    contains,
    tolerance: float,
) -> Optional[Point]:
    """Quadtree best-first search for the point furthest from ``boundary``."""
    tiebreak = itertools.count()
    heap: list[Tuple[float, int, _Cell]] = []

    def push(cell: _Cell) -> None:
        heapq.heappush(heap, (-cell[0], next(tiebreak), cell))

    best: Optional[_Cell] = None
    for cell in _seed_cells(polygon, boundary, contains):
        if best is None or cell[1] > best[1]:
            best = cell
        push(cell)

    # The centroid is often already the answer for convex-ish polygons, and
    # seeding it raises the initial bar so that more cells get pruned.
    centroid = polygon.centroid
    if contains(centroid):
        cell = _cell(centroid.x, centroid.y, 0.0, boundary, contains)
        if best is None or cell[1] > best[1]:
            best = cell

    for _ in range(_MAX_ITERATIONS):
        if not heap:
            break
        _, _, (upper_bound, _, x, y, half) = heapq.heappop(heap)
        if best is not None and upper_bound - best[1] <= tolerance:
            break  # no remaining cell can meaningfully beat the best point

        quarter = half / 2.0
        for dx, dy in ((-quarter, -quarter), (quarter, -quarter),
                       (-quarter, quarter), (quarter, quarter)):
            child = _cell(x + dx, y + dy, quarter, boundary, contains)
            if best is None or child[1] > best[1]:
                best = child
            push(child)

    if best is None or best[1] <= 0.0:
        return None
    return Point(best[2], best[3])


def _seed_cells(
    polygon: Polygon,
    boundary: BaseGeometry,
    contains,
) -> Iterator[_Cell]:
    """Yield a grid of cells covering the polygon's bounding box."""
    minx, miny, maxx, maxy = polygon.bounds
    width, height = maxx - minx, maxy - miny
    long_side, short_side = max(width, height), min(width, height)
    size = max(short_side, long_side / _MAX_SEED_CELLS)
    half = size / 2.0

    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            yield _cell(x + half, y + half, half, boundary, contains)
            y += size
        x += size


def _cell(x: float, y: float, half: float, boundary: BaseGeometry, contains) -> _Cell:
    """Build a cell, scoring it by signed distance from the boundary.

    Points outside the polygon - including points inside a hole - score
    negative, so they are only ever explored for the sake of the interior
    points their cell might still contain.
    """
    point = Point(x, y)
    distance = point.distance(boundary)
    if not contains(point):
        distance = -distance
    # Upper bound on any point in this cell: its centre distance plus the
    # cell's half-diagonal.  This is what makes the best-first pruning exact.
    return (distance + half * _SQRT2, distance, x, y, half)


def _largest_polygon(geometry: BaseGeometry) -> Optional[Polygon]:
    """Return the largest ``Polygon`` anywhere inside ``geometry``, if any."""
    best: Optional[Polygon] = None
    stack = [geometry]
    while stack:
        part = stack.pop()
        if part.is_empty:
            continue
        if isinstance(part, Polygon):
            if best is None or part.area > best.area:
                best = part
        else:
            stack.extend(getattr(part, "geoms", ()))
    return best
```