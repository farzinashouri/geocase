I'll write a module using `shapely.ops.voronoi_diagram` with an oversized envelope, then clip each cell to the given rectangle and match cells back to their generating points via an STRtree.

```python
"""Voronoi diagram clipped to a rectangular boundary."""

from shapely.geometry import MultiPoint, Point, Polygon, box
from shapely.ops import voronoi_diagram
from shapely.strtree import STRtree


def voronoi_cells(points, bounds):
    """Return N polygons, the Voronoi cell of each input point clipped to bounds.

    points: list of N distinct (x, y) tuples.
    bounds: (minx, miny, maxx, maxy) rectangle containing all points.
    """
    minx, miny, maxx, maxy = bounds
    rect = box(minx, miny, maxx, maxy)

    n = len(points)
    if n == 0:
        return []
    if n == 1:
        return [rect]

    width = maxx - minx
    height = maxy - miny
    margin = max(width, height, 1.0) * 4.0 + 1.0
    envelope = box(minx - margin, miny - margin, maxx + margin, maxy + margin)

    multipoint = MultiPoint([Point(x, y) for x, y in points])
    diagram = voronoi_diagram(multipoint, envelope=envelope)

    clipped_cells = []
    for cell in diagram.geoms:
        clipped = rect.intersection(cell)
        if not isinstance(clipped, Polygon):
            for part in getattr(clipped, "geoms", []):
                if isinstance(part, Polygon):
                    clipped = part
                    break
        clipped_cells.append(clipped)

    tree = STRtree(clipped_cells)

    result = [None] * n
    for i, (x, y) in enumerate(points):
        p = Point(x, y)
        chosen = None
        for ci in tree.query(p, predicate="intersects"):
            if clipped_cells[ci].covers(p):
                chosen = clipped_cells[ci]
                break
        if chosen is None:
            chosen = min(clipped_cells, key=lambda c: p.distance(c))
        result[i] = chosen

    return result
```