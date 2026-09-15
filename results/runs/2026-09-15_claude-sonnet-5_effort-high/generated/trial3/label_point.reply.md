```python
"""Compute a good label point for a shapely Polygon."""

from __future__ import annotations

import heapq
import math

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon


class _Cell:
    __slots__ = ("x", "y", "h", "d", "max")

    def __init__(self, x: float, y: float, h: float, polygon: Polygon) -> None:
        self.x = x
        self.y = y
        self.h = h
        self.d = _signed_distance(polygon, x, y)
        self.max = self.d + self.h * math.sqrt(2)

    def __lt__(self, other: "_Cell") -> bool:
        # heapq is a min-heap; we want the cell with the largest potential first.
        return self.max > other.max


def _signed_distance(polygon: Polygon, x: float, y: float) -> float:
    point = Point(x, y)
    distance = point.distance(polygon.exterior)
    for interior in polygon.interiors:
        distance = min(distance, point.distance(interior))
    if polygon.contains(point):
        return distance
    return -distance


def _polylabel(polygon: Polygon, precision: float) -> Point:
    """Approximate the pole of inaccessibility (Mapbox's polylabel algorithm)."""
    minx, miny, maxx, maxy = polygon.bounds
    width = maxx - minx
    height = maxy - miny
    if width <= 0 or height <= 0:
        return polygon.representative_point()

    cell_size = min(width, height)
    h = cell_size / 2.0

    cells: list[_Cell] = []
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            cells.append(_Cell(x + h, y + h, h, polygon))
            y += cell_size
        x += cell_size

    if not cells:
        return polygon.representative_point()

    heapq.heapify(cells)

    centroid = polygon.centroid
    best = _Cell(centroid.x, centroid.y, 0.0, polygon)

    bbox_cell = _Cell(minx + width / 2.0, miny + height / 2.0, 0.0, polygon)
    if bbox_cell.d > best.d:
        best = bbox_cell

    while cells:
        cell = heapq.heappop(cells)

        if cell.d > best.d:
            best = cell

        if cell.max - best.d <= precision:
            continue

        half = cell.h / 2.0
        for dx, dy in ((-half, -half), (half, -half), (-half, half), (half, half)):
            heapq.heappush(cells, _Cell(cell.x + dx, cell.y + dy, half, polygon))

    return Point(best.x, best.y)


def label_point(polygon: Polygon) -> Point:
    """Return a point inside ``polygon`` suitable for placing a text label."""
    if polygon.is_empty:
        raise ValueError("cannot compute a label point for an empty polygon")

    work_polygon = polygon
    if not work_polygon.is_valid:
        repaired = work_polygon.buffer(0)
        if repaired.is_empty:
            raise ValueError("polygon is invalid and could not be repaired")
        if hasattr(repaired, "geoms"):
            repaired = max(repaired.geoms, key=lambda g: g.area)
        work_polygon = repaired

    minx, miny, maxx, maxy = work_polygon.bounds
    size = max(maxx - minx, maxy - miny)
    precision = max(size / 1000.0, 1e-9)

    point = _polylabel(work_polygon, precision)

    if not work_polygon.contains(point):
        point = work_polygon.representative_point()

    return point
```