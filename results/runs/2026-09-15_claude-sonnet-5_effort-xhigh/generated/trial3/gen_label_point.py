"""Label point placement for polygons using the pole-of-inaccessibility algorithm.

The pole of inaccessibility is the point inside a polygon that is farthest
from any edge (including edges of holes). It tends to produce much better
label placements than the centroid, which can fall outside concave polygons
or land close to an edge in irregular shapes.
"""

from __future__ import annotations

import heapq
import itertools
import math
from typing import Optional

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon


def _signed_distance(polygon: Polygon, x: float, y: float) -> float:
    """Distance from (x, y) to the polygon boundary; negative if outside."""
    point = Point(x, y)
    distance = polygon.boundary.distance(point)
    return distance if polygon.contains(point) else -distance


def label_point(polygon: Polygon, precision: Optional[float] = None) -> Point:
    """Find a point inside ``polygon`` suitable for placing a text label.

    Uses the pole-of-inaccessibility algorithm (as popularized by Mapbox's
    polylabel) to locate the point inside the polygon that is farthest from
    any boundary, which is a robust choice for label placement on concave
    or irregular shapes.

    Args:
        polygon: A shapely Polygon, in any coordinate system.
        precision: Stopping tolerance, in the polygon's own coordinate
            units. Defaults to roughly 1% of the smaller bounding-box
            dimension, which scales sensibly for both geographic
            (degree-based) and projected (meter-based) inputs.

    Returns:
        A shapely Point guaranteed to lie inside ``polygon``.
    """
    if polygon.is_empty:
        raise ValueError("Cannot compute a label point for an empty polygon.")

    working_polygon = polygon if polygon.is_valid else polygon.buffer(0)

    min_x, min_y, max_x, max_y = working_polygon.bounds
    width = max_x - min_x
    height = max_y - min_y

    if width <= 0 or height <= 0 or working_polygon.area == 0:
        return working_polygon.representative_point()

    if precision is None:
        precision = min(width, height) / 100.0

    cell_size = min(width, height)
    half = cell_size / 2.0

    centroid = working_polygon.centroid
    best_x, best_y = centroid.x, centroid.y
    best_distance = _signed_distance(working_polygon, best_x, best_y)

    bbox_center_x = min_x + width / 2.0
    bbox_center_y = min_y + height / 2.0
    bbox_distance = _signed_distance(working_polygon, bbox_center_x, bbox_center_y)
    if bbox_distance > best_distance:
        best_x, best_y, best_distance = bbox_center_x, bbox_center_y, bbox_distance

    queue: list = []
    counter = itertools.count()

    def push(x: float, y: float, h: float) -> None:
        distance = _signed_distance(working_polygon, x, y)
        max_distance = distance + h * math.sqrt(2.0)
        heapq.heappush(queue, (-max_distance, next(counter), x, y, h, distance))

    x = min_x
    while x < max_x:
        y = min_y
        while y < max_y:
            push(x + half, y + half, half)
            y += cell_size
        x += cell_size

    while queue:
        neg_max_distance, _, x, y, h, distance = heapq.heappop(queue)
        max_distance = -neg_max_distance

        if distance > best_distance:
            best_x, best_y, best_distance = x, y, distance

        if max_distance - best_distance <= precision:
            continue

        quarter = h / 2.0
        push(x - quarter, y - quarter, quarter)
        push(x + quarter, y - quarter, quarter)
        push(x - quarter, y + quarter, quarter)
        push(x + quarter, y + quarter, quarter)

    best_point = Point(best_x, best_y)
    if working_polygon.contains(best_point):
        return best_point
    return working_polygon.representative_point()