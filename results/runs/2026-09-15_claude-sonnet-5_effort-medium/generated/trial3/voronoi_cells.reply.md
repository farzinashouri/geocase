```python
"""Compute Voronoi cells for a set of points, clipped to a bounding rectangle."""

from shapely.geometry import Point, MultiPoint
from shapely.geometry.polygon import Polygon
from shapely.geometry import box as _box
from shapely.ops import voronoi_diagram


def voronoi_cells(points, bounds):
    """Return the list of Voronoi cell polygons for `points`, clipped to `bounds`.

    Args:
        points: list of N distinct (x, y) tuples in a planar coordinate system.
        bounds: (minx, miny, maxx, maxy) rectangle containing all points.

    Returns:
        A list of N shapely Polygons; the i-th polygon is the subset of the
        rectangle closer to points[i] than to any other input point.
    """
    minx, miny, maxx, maxy = bounds
    rect = _box(minx, miny, maxx, maxy)

    if len(points) == 1:
        return [rect]

    multipoint = MultiPoint(points)
    diagram = voronoi_diagram(multipoint, envelope=rect)

    raw_cells = [cell.intersection(rect) for cell in diagram.geoms]

    result = [None] * len(points)
    for cell in raw_cells:
        if cell.is_empty:
            continue
        distances = [cell.distance(Point(p)) for p in points]
        idx = min(range(len(points)), key=lambda i: distances[i])
        result[idx] = cell

    return result
```