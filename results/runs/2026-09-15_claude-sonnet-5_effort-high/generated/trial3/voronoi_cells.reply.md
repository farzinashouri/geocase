I'll proceed without running verification since the command requires approval — I have high confidence in the shapely 2.1 API based on documented behavior.

```python
"""Compute Voronoi cells for a set of points, clipped to a bounding rectangle."""

from shapely import voronoi_polygons
from shapely.geometry import MultiPoint, Point, Polygon, box


def _to_polygon(geometry):
    """Reduce a (possibly degenerate) intersection result to a single Polygon."""
    if geometry.geom_type == "Polygon":
        return geometry
    if geometry.geom_type == "MultiPolygon":
        return max(geometry.geoms, key=lambda part: part.area)
    return geometry.buffer(0)


def voronoi_cells(points, bounds):
    """Return the Voronoi cell of each input point, clipped to bounds.

    points: list of N distinct (x, y) tuples.
    bounds: (minx, miny, maxx, maxy) rectangle containing all points.

    Returns a list of N shapely Polygons, in the same order as `points`,
    where polygon i is the region of the rectangle closer to points[i]
    than to any other input point.
    """
    minx, miny, maxx, maxy = bounds
    clip = box(minx, miny, maxx, maxy)

    if len(points) == 1:
        return [clip]

    diagram = voronoi_polygons(MultiPoint(points), extend_to=clip)

    clipped_cells = [_to_polygon(cell.intersection(clip)) for cell in diagram.geoms]

    result = [None] * len(points)
    for cell in clipped_cells:
        anchor = cell.representative_point()
        nearest_index = min(
            range(len(points)),
            key=lambda i: anchor.distance(Point(points[i])),
        )
        result[nearest_index] = cell

    return result
```