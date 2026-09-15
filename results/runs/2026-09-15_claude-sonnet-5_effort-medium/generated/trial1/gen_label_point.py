"""Compute a point suitable for labeling a shapely Polygon."""

from __future__ import annotations

import heapq
import itertools

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon


class _Cell:
    __slots__ = ("x", "y", "half", "distance", "max_distance")

    def __init__(self, x: float, y: float, half: float, polygon: Polygon):
        self.x = x
        self.y = y
        self.half = half
        self.distance = polygon.boundary.distance(Point(x, y))
        if polygon.contains(Point(x, y)):
            self.max_distance = self.distance + half * (2 ** 0.5)
        else:
            self.max_distance = -self.distance + half * (2 ** 0.5)


def _polylabel(polygon: Polygon, precision: float) -> Point:
    minx, miny, maxx, maxy = polygon.bounds
    width = maxx - minx
    height = maxy - miny
    if width == 0 or height == 0:
        return polygon.representative_point()

    cell_size = min(width, height)
    half = cell_size / 2.0

    counter = itertools.count()
    cell_queue: list[tuple[float, int, _Cell]] = []

    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            c = _Cell(x + half, y + half, half, polygon)
            heapq.heappush(cell_queue, (-c.max_distance, next(counter), c))
            y += cell_size
        x += cell_size

    best = _Cell(minx + width / 2.0, miny + height / 2.0, 0, polygon)
    bbox_cell = _Cell(minx + width / 2.0, miny + height / 2.0, 0, polygon)
    if bbox_cell.distance > best.distance:
        best = bbox_cell

    while cell_queue:
        _, _, cell = heapq.heappop(cell_queue)

        if cell.distance > best.distance:
            best = cell

        if cell.max_distance - best.distance <= precision:
            continue

        h = cell.half / 2.0
        for dx, dy in ((-h, -h), (h, -h), (-h, h), (h, h)):
            c = _Cell(cell.x + dx, cell.y + dy, h, polygon)
            heapq.heappush(cell_queue, (-c.max_distance, next(counter), c))

    return Point(best.x, best.y)


def label_point(polygon: Polygon) -> Point:
    """Return a Point inside `polygon` suitable for placing a text label."""
    if polygon.is_empty:
        raise ValueError("Cannot compute a label point for an empty polygon")

    minx, miny, maxx, maxy = polygon.bounds
    precision = max(maxx - minx, maxy - miny) / 1000.0 or 1e-9

    try:
        point = _polylabel(polygon, precision)
    except Exception:
        point = None

    if point is not None and polygon.contains(point):
        return point

    centroid = polygon.centroid
    if polygon.contains(centroid):
        return centroid

    return polygon.representative_point()