```python
from shapely.geometry import Polygon, MultiPoint
from shapely.ops import voronoi_polygons

def voronoi_cells(points, bounds):
    """
    Compute Voronoi cells for a set of points clipped to a bounding rectangle.

    Parameters
    ----------
    points : list[tuple[float, float]]
        List of (x, y) coordinates. All points must be distinct.
    bounds : tuple[float, float, float, float]
        Bounding rectangle (minx, miny, maxx, maxy) containing all points.

    Returns
    -------
    list[shapely.Polygon]
        List of Voronoi cell polygons in the same order as input points.
    """
    minx, miny, maxx, maxy = bounds
    bounding_poly = Polygon([(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)])
    mp = MultiPoint(points)
    voronoi = voronoi_polygons(mp, extend_to=bounding_poly)
    return list(voronoi.geoms)
```