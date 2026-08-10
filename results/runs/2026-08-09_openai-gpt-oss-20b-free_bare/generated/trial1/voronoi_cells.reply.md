```python
from shapely.geometry import Point, box
from shapely.ops import voronoi_diagram

def voronoi_cells(points, bounds):
    """
    Compute the Voronoi cells of a set of points clipped to a bounding rectangle.

    Parameters
    ----------
    points : list[tuple[float, float]]
        A list of N distinct (x, y) tuples in a projected coordinate system.
    bounds : tuple[float, float, float, float]
        A rectangle (minx, miny, maxx, maxy) that contains all the points.

    Returns
    -------
    list[shapely.geometry.Polygon]
        A list of N polygons. The i-th polygon is the part of the rectangle
        that is closer to the i-th input point than to any other point.
    """
    if not points:
        return []

    minx, miny, maxx, maxy = bounds
    envelope = box(minx, miny, maxx, maxy)

    # Create shapely Point objects
    point_objs = [Point(p) for p in points]

    # Compute the Voronoi diagram clipped to the envelope
    diagram = voronoi_diagram(point_objs, envelope=envelope, tolerance=1e-6)

    # Extract polygons from the resulting geometry collection
    if hasattr(diagram, "geoms"):
        polygons = list(diagram.geoms)
    else:
        polygons = [diagram]

    # Map each input point to its corresponding cell
    cells = []
    for pt in point_objs:
        cell = None
        # First try to find a polygon that covers the point
        for poly in polygons:
            if poly.covers(pt):
                cell = poly
                break
        # If none covers the point (unlikely), pick the nearest polygon
        if cell is None:
            min_dist = None
            for poly in polygons:
                d = poly.distance(pt)
                if min_dist is None or d < min_dist:
                    min_dist = d
                    cell = poly
        cells.append(cell)

    return cells
```