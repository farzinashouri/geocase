```python
"""Compute a point suitable for placing a text label inside a polygon.

Uses a variant of the "polylabel" algorithm (quadtree-based search for the
pole of inaccessibility): the point inside the polygon that is farthest
from any edge, which tends to produce visually pleasing label placement.
"""

import heapq
from itertools import count

from shapely.geometry import Point, Polygon


class _Cell:
    __slots__ = ("x", "y", "half", "distance", "max_distance")

    def __init__(self, x, y, half, polygon, boundary):
        self.x = x
        self.y = y
        self.half = half
        d = boundary.distance(Point(x, y))
        self.distance = d if polygon.contains(Point(x, y)) else -d
        self.max_distance = self.distance + half * 1.4142135623730951


def _polylabel(polygon, precision):
    boundary = polygon.boundary
    minx, miny, maxx, maxy = polygon.bounds
    width = maxx - minx
    height = maxy - miny
    cell_size = min(width, height)

    if cell_size == 0:
        return Point(minx, miny)

    half = cell_size / 2.0
    counter = count()
    queue = []

    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            cell = _Cell(x + half, y + half, half, polygon, boundary)
            heapq.heappush(queue, (-cell.max_distance, next(counter), cell))
            y += cell_size
        x += cell_size

    best = _Cell(minx + width / 2.0, miny + height / 2.0, 0, polygon, boundary)

    while queue:
        _, _, cell = heapq.heappop(queue)

        if cell.distance > best.distance:
            best = cell

        if cell.max_distance - best.distance <= precision:
            continue

        child_half = cell.half / 2.0
        for dx, dy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            child = _Cell(
                cell.x + dx * child_half,
                cell.y + dy * child_half,
                child_half,
                polygon,
                boundary,
            )
            heapq.heappush(queue, (-child.max_distance, next(counter), child))

    return Point(best.x, best.y)


def label_point(polygon: Polygon) -> Point:
    """Return a point inside *polygon* suitable for placing a text label.

    The point is chosen to be far from the polygon's boundary (and any
    holes) when possible, falling back to a guaranteed-interior point for
    degenerate geometries.
    """
    if polygon.is_empty:
        raise ValueError("polygon is empty")

    representative = polygon.representative_point()

    if polygon.area == 0:
        return representative

    minx, miny, maxx, maxy = polygon.bounds
    precision = max(maxx - minx, maxy - miny) / 500.0 or 1e-9

    try:
        point = _polylabel(polygon, precision)
    except Exception:
        return representative

    if polygon.contains(point):
        return point

    return representative
```