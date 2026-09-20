"""Compute a point inside a polygon suitable for placing a text label.

Uses an approximation of the "pole of inaccessibility" (the point inside
the polygon that is farthest from its boundary), found via Mapbox's
polylabel grid-subdivision algorithm. This tends to produce much better
label placements than a centroid or an arbitrary interior point, since it
naturally avoids concavities, holes, and thin polygon arms.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from math import ceil, sqrt

from shapely.geometry import Point, Polygon

_MAX_GRID_CELLS_PER_AXIS = 64


@dataclass(order=True)
class _Cell:
    priority: float
    x: float = field(compare=False)
    y: float = field(compare=False)
    half_size: float = field(compare=False)
    distance: float = field(compare=False)


def _signed_distance(x: float, y: float, polygon: Polygon) -> float:
    point = Point(x, y)
    distance = polygon.boundary.distance(point)
    return distance if polygon.contains(point) else -distance


def _make_cell(x: float, y: float, half_size: float, polygon: Polygon) -> _Cell:
    distance = _signed_distance(x, y, polygon)
    # Negated upper bound on the distance achievable anywhere in this cell,
    # so that a min-heap pops the most promising cell first.
    priority = -(distance + half_size * sqrt(2))
    return _Cell(priority=priority, x=x, y=y, half_size=half_size, distance=distance)


def _pole_of_inaccessibility(polygon: Polygon, precision: float) -> Point:
    minx, miny, maxx, maxy = polygon.bounds
    width = maxx - minx
    height = maxy - miny
    if width <= 0 or height <= 0:
        return polygon.representative_point()

    cell_size = max(min(width, height), max(width, height) / _MAX_GRID_CELLS_PER_AXIS)
    half = cell_size / 2.0

    cell_queue: list[_Cell] = []
    num_x = max(1, int(ceil(width / cell_size)))
    num_y = max(1, int(ceil(height / cell_size)))
    for i in range(num_x):
        for j in range(num_y):
            cell_queue.append(_make_cell(minx + (i + 0.5) * cell_size, miny + (j + 0.5) * cell_size, half, polygon))
    heapq.heapify(cell_queue)

    best = _make_cell(minx + width / 2.0, miny + height / 2.0, 0.0, polygon)

    centroid = polygon.centroid
    centroid_cell = _make_cell(centroid.x, centroid.y, 0.0, polygon)
    if centroid_cell.distance > best.distance:
        best = centroid_cell

    while cell_queue:
        cell = heapq.heappop(cell_queue)

        if cell.distance > best.distance:
            best = cell

        if -cell.priority - best.distance <= precision:
            continue

        h = cell.half_size / 2.0
        for dx, dy in ((-h, -h), (h, -h), (-h, h), (h, h)):
            heapq.heappush(cell_queue, _make_cell(cell.x + dx, cell.y + dy, h, polygon))

    return Point(best.x, best.y)


def label_point(polygon: Polygon) -> Point:
    """Return a point inside ``polygon`` suitable for placing a text label."""
    if polygon.is_empty:
        raise ValueError("Cannot compute a label point for an empty polygon")

    minx, miny, maxx, maxy = polygon.bounds
    size = max(maxx - minx, maxy - miny)
    precision = size / 1000.0 if size > 0 else 1e-9

    point = _pole_of_inaccessibility(polygon, precision)

    if not polygon.contains(point):
        point = polygon.representative_point()

    return point