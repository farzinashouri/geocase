"""Compute a good label point (pole of inaccessibility) for a polygon."""

import heapq
import math

from shapely.geometry import Point, Polygon


def label_point(polygon: Polygon) -> Point:
    if polygon is None or polygon.is_empty:
        raise ValueError("polygon must be a non-empty Polygon")

    minx, miny, maxx, maxy = polygon.bounds
    width = maxx - minx
    height = maxy - miny

    if width <= 0 or height <= 0:
        result = polygon.representative_point()
        return result if polygon.contains(result) else polygon.centroid

    boundary = polygon.boundary
    sqrt2 = math.sqrt(2)

    def cell_distance(x: float, y: float) -> float:
        pt = Point(x, y)
        d = boundary.distance(pt)
        return d if polygon.contains(pt) else -d

    cell_size = min(width, height)
    h = cell_size / 2.0
    precision = max(cell_size / 100.0, 1e-9)

    queue = []
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            cx, cy = x + h, y + h
            d = cell_distance(cx, cy)
            heapq.heappush(queue, (-(d + h * sqrt2), cx, cy, h, d))
            y += cell_size
        x += cell_size

    bbox_cx, bbox_cy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
    bbox_d = cell_distance(bbox_cx, bbox_cy)
    heapq.heappush(queue, (-(bbox_d + h * sqrt2), bbox_cx, bbox_cy, h, bbox_d))

    best_x, best_y, best_d = bbox_cx, bbox_cy, bbox_d

    centroid = polygon.centroid
    if polygon.contains(centroid):
        cd = cell_distance(centroid.x, centroid.y)
        if cd > best_d:
            best_x, best_y, best_d = centroid.x, centroid.y, cd

    while queue:
        neg_max_potential, x, y, h, d = heapq.heappop(queue)
        max_potential = -neg_max_potential

        if d > best_d:
            best_x, best_y, best_d = x, y, d

        if max_potential - best_d <= precision:
            continue

        h2 = h / 2.0
        for dx, dy in ((-h2, -h2), (h2, -h2), (-h2, h2), (h2, h2)):
            nx, ny = x + dx, y + dy
            nd = cell_distance(nx, ny)
            heapq.heappush(queue, (-(nd + h2 * sqrt2), nx, ny, h2, nd))

    result = Point(best_x, best_y)
    if not polygon.contains(result):
        result = polygon.representative_point()
    return result