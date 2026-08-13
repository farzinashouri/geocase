```python
from shapely.geometry import Point, Polygon, MultiPoint
from shapely.ops import voronoi_polygons

def voronoi_cells(points, bounds):
    """
    Compute Voronoi cells for a set of points clipped to a rectangular bounds.

    Parameters
    ----------
    points : list[tuple[float, float]]
        List of (x, y) coordinates.
    bounds : tuple[float, float, float, float]
        Rectangle (minx, miny, maxx, maxy) containing all points.

    Returns
    -------
    list[shapely.Polygon]
        List of Voronoi cell polygons in the same order as input points.
    """
    if not points:
        return []

    # Create shapely Points preserving input order
    geom_points = [Point(x, y) for x, y in points]

    # Create envelope polygon from bounds
    minx, miny, maxx, maxy = bounds
    envelope = Polygon([
        (minx, miny),
        (maxx, miny),
        (maxx, maxy),
        (minx, maxy),
        (minx, miny)
    ])

    # Compute Voronoi polygons clipped to envelope
    # The returned GeometryCollection contains polygons in the same order as the input points.
    voronoi = voronoi_polygons(MultiPoint(geom_points), envelope=envelope)

    # Extract polygons as a list
    return list(voronoi.geoms)
```