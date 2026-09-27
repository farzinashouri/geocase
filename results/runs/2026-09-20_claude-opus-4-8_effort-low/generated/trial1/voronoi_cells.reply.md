```python
"""Compute Voronoi cells clipped to a bounding rectangle.

Each returned polygon is the set of points within the rectangle that are
closer to the corresponding input point than to any other input point.
"""

from shapely import MultiPoint, Point, voronoi_polygons
from shapely.geometry import box
from shapely.strtree import STRtree


def voronoi_cells(points, bounds):
    """Return per-point Voronoi cells clipped to ``bounds``.

    ``points`` is a list of N distinct ``(x, y)`` tuples in a planar
    coordinate system. ``bounds`` is ``(minx, miny, maxx, maxy)`` and must
    contain every point. Returns a list of N shapely ``Polygon``s, where the
    i-th polygon is exactly the part of the rectangle whose locations are
    closer to ``points[i]`` than to any other input point.
    """
    minx, miny, maxx, maxy = bounds
    rectangle = box(minx, miny, maxx, maxy)

    pts = [Point(x, y) for x, y in points]

    # Single point: the whole rectangle is its cell.
    if len(pts) == 1:
        return [rectangle]

    mp = MultiPoint(pts)

    # Extend the diagram well beyond the rectangle so no cell is truncated
    # before we clip it ourselves.
    span = max(maxx - minx, maxy - miny)
    extend = box(
        minx - span - 1.0,
        miny - span - 1.0,
        maxx + span + 1.0,
        maxy + span + 1.0,
    )

    cells = list(voronoi_polygons(mp, extend_to=extend).geoms)

    # Match each raw cell back to the input point it contains, using an
    # index over the input points for efficiency.
    tree = STRtree(pts)
    result = [None] * len(pts)
    for cell in cells:
        clipped = cell.intersection(rectangle)
        if clipped.is_empty:
            continue
        # The generating point is the one lying inside this cell.
        candidates = tree.query(cell)
        for idx in candidates:
            if cell.covers(pts[int(idx)]):
                result[int(idx)] = clipped
                break

    # Fallback for any point not matched (e.g. numerical edge cases):
    # assign the rectangle region nearest to it. This should be rare.
    for i, poly in enumerate(result):
        if poly is None:
            result[i] = rectangle.intersection(
                _nearest_region(pts, i, rectangle)
            )
    return result


def _nearest_region(pts, i, rectangle):
    """Brute-force nearest-point region for point ``i`` within ``rectangle``.

    Used only as a defensive fallback when the vectorized matching misses a
    point. Builds the region as the intersection of half-planes bisecting
    ``pts[i]`` against every other point.
    """
    region = rectangle
    xi, yi = pts[i].x, pts[i].y
    minx, miny, maxx, maxy = rectangle.bounds
    diag = ((maxx - minx) ** 2 + (maxy - miny) ** 2) ** 0.5
    for j, pj in enumerate(pts):
        if j == i:
            continue
        xj, yj = pj.x, pj.y
        mx, my = (xi + xj) / 2.0, (yi + yj) / 2.0
        dx, dy = xj - xi, yj - yi
        norm = (dx * dx + dy * dy) ** 0.5
        if norm == 0:
            continue
        # Perpendicular to the (i, j) direction, offset far in both ways.
        px, py = -dy / norm, dx / norm
        ext = diag + 1.0
        # Half-plane on the side of pts[i]: build a large box and clip.
        from shapely.geometry import Polygon

        far = diag * 2 + 1.0
        # Points defining the half-plane polygon on pts[i]'s side.
        a = (mx + px * ext, my + py * ext)
        b = (mx - px * ext, my - py * ext)
        c = (b[0] - dx / norm * far, b[1] - dy / norm * far)
        d = (a[0] - dx / norm * far, a[1] - dy / norm * far)
        half = Polygon([a, b, c, d])
        region = region.intersection(half)
    return region
```