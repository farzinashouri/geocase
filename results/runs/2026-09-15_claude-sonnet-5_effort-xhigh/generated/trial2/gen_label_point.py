"""Compute a good point for drawing a text label inside a polygon.

Uses the "pole of inaccessibility" approach (as popularized by Mapbox's
polylabel): repeatedly subdivide the polygon's bounding box, tracking the
point that maximizes distance to the polygon boundary. This tends to give
a more visually centered result than the centroid for concave or irregular
shapes, and unlike the centroid it is guaranteed to fall inside the
polygon.
"""

from __future__ import annotations

import heapq
import math

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from shapely.prepared import prep


class _Cell:
    __slots__ = ("x", "y", "h", "d", "max_dist")

    def __init__(self, x: float, y: float, h: float, polygon: Polygon, prepared) -> None:
        self.x = x
        self.y = y
        self.h = h
        point = Point(x, y)
        distance = polygon.boundary.distance(point)
        self.d = distance if prepared.contains(point) else -distance
        self.max_dist = self.d + h * math.sqrt(2.0)

    def __lt__(self, other: "_Cell") -> bool:
        # heapq is a min-heap; invert the comparison so the cell with the
        # largest upper-bound distance is popped first.
        return self.max_dist > other.max_dist


def _polylabel(polygon: Polygon, precision: float) -> Point:
    prepared = prep(polygon)
    minx, miny, maxx, maxy = polygon.bounds
    width = maxx - minx
    height = maxy - miny

    if width <= 0 or height <= 0:
        return polygon.representative_point()

    cell_size = min(width, height)
    h = cell_size / 2.0

    heap: list[_Cell] = []
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            heap.append(_Cell(x + h, y + h, h, polygon, prepared))
            y += cell_size
        x += cell_size
    heapq.heapify(heap)

    best = max(heap, key=lambda c: c.d)

    while heap:
        cell = heapq.heappop(heap)

        if cell.d > best.d:
            best = cell

        if cell.max_dist - best.d <= precision:
            continue

        half = cell.h / 2.0
        for dx, dy in ((-half, -half), (half, -half), (-half, half), (half, half)):
            heapq.heappush(heap, _Cell(cell.x + dx, cell.y + dy, half, polygon, prepared))

    return Point(best.x, best.y)


def label_point(polygon: Polygon) -> Point:
    """Return a `Point` inside `polygon` suitable for placing a text label.

    Works in any coordinate system, since the search precision is derived
    from the polygon's own bounding box rather than a fixed unit.
    """
    if polygon.is_empty:
        raise ValueError("cannot compute a label point for an empty polygon")

    minx, miny, maxx, maxy = polygon.bounds
    span = max(maxx - minx, maxy - miny)
    precision = span * 0.001 if span > 0 else 1e-9

    point = _polylabel(polygon, precision)

    if not polygon.contains(point):
        point = polygon.representative_point()

    return point