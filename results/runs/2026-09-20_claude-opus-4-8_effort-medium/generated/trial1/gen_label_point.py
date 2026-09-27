"""Compute a label point (visual center) for a shapely Polygon.

The returned point is guaranteed to lie inside the polygon.  It is computed
via the "pole of inaccessibility" -- the interior point that is farthest from
the polygon boundary -- which is a much better anchor for a text label than
the centroid (the centroid can fall outside concave or holed polygons).

Importing this module has no side effects.
"""

from __future__ import annotations

import heapq
from math import sqrt

from shapely.geometry import Point, Polygon


def _cell_center_distance(px: float, py: float, polygon: Polygon) -> float:
    """Signed distance from (px, py) to the polygon boundary.

    Positive when the point is inside the polygon, negative when outside.
    """
    pt = Point(px, py)
    dist = polygon.exterior.distance(pt)
    for ring in polygon.interiors:
        dist = min(dist, ring.distance(pt))
    return dist if polygon.contains(pt) else -dist


class _Cell:
    __slots__ = ("x", "y", "h", "d", "max_d")

    def __init__(self, x: float, y: float, h: float, polygon: Polygon) -> None:
        self.x = x
        self.y = y
        self.h = h  # half the cell size
        self.d = _cell_center_distance(x, y, polygon)  # dist to boundary
        # Upper bound on the distance achievable anywhere within this cell.
        self.max_d = self.d + h * sqrt(2)

    # Priority queue orders by the most promising cell first (largest max_d).
    def __lt__(self, other: "_Cell") -> bool:
        return self.max_d > other.max_d


def _polylabel(polygon: Polygon, precision: float) -> Point:
    """Find the pole of inaccessibility of ``polygon``.

    A port of Mapbox's polylabel algorithm.
    """
    minx, miny, maxx, maxy = polygon.bounds
    width = maxx - minx
    height = maxy - miny
    cell_size = min(width, height)

    if cell_size == 0:
        # Degenerate (zero-area) bounds; fall back to a guaranteed point.
        return polygon.representative_point()

    h = cell_size / 2.0

    # Seed a coarse grid covering the bounding box.
    queue: list[_Cell] = []
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            heapq.heappush(queue, _Cell(x + h, y + h, h, polygon))
            y += cell_size
        x += cell_size

    # First candidate: the centroid (falls back to a valid point if outside).
    def centroid_cell(poly: Polygon) -> _Cell:
        c = poly.centroid
        if not poly.contains(c):
            c = poly.representative_point()
        return _Cell(c.x, c.y, 0.0, poly)

    best = centroid_cell(polygon)

    # Also try the center of the bounding box.
    bbox_cell = _Cell(minx + width / 2.0, miny + height / 2.0, 0.0, polygon)
    if bbox_cell.d > best.d:
        best = bbox_cell

    while queue:
        cell = heapq.heappop(queue)

        if cell.d > best.d:
            best = cell

        # Discard cells that cannot possibly beat the best found so far.
        if cell.max_d - best.d <= precision:
            continue

        # Subdivide into four child cells.
        nh = cell.h / 2.0
        heapq.heappush(queue, _Cell(cell.x - nh, cell.y - nh, nh, polygon))
        heapq.heappush(queue, _Cell(cell.x + nh, cell.y - nh, nh, polygon))
        heapq.heappush(queue, _Cell(cell.x - nh, cell.y + nh, nh, polygon))
        heapq.heappush(queue, _Cell(cell.x + nh, cell.y + nh, nh, polygon))

    return Point(best.x, best.y)


def label_point(polygon: Polygon) -> Point:
    """Return a ``Point`` inside ``polygon`` suitable for anchoring a label.

    The point is the polygon's pole of inaccessibility (the interior point
    farthest from the boundary), which is stable for concave polygons and
    polygons with holes.  The result is guaranteed to lie inside the polygon.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        The polygon to label, in any coordinate system.

    Returns
    -------
    shapely.geometry.Point
        A point contained within ``polygon``.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        raise ValueError("cannot compute a label point for an empty polygon")
    if not polygon.is_valid:
        # Repair self-intersections etc.; may yield a MultiPolygon.
        repaired = polygon.buffer(0)
        if repaired.is_empty:
            return polygon.representative_point()
        if repaired.geom_type == "MultiPolygon":
            # Label the largest component.
            repaired = max(repaired.geoms, key=lambda g: g.area)
        if isinstance(repaired, Polygon):
            polygon = repaired

    # Scale the target precision to the polygon's size.
    minx, miny, maxx, maxy = polygon.bounds
    extent = min(maxx - minx, maxy - miny)
    precision = extent / 1000.0 if extent > 0 else 0.0

    point = _polylabel(polygon, precision)

    # Final safety net: never return a point outside the polygon.
    if not polygon.contains(point):
        point = polygon.representative_point()
    return point