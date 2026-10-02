from shapely.geometry import MultiPoint, box
from shapely.ops import voronoi_polygons

def voronoi_cells(points, bounds):
    """
    Compute Voronoi cells for a set of points clipped to a bounding rectangle.

    Parameters
    ----------
    points : list[tuple[float, float]]
        List of (x, y) coordinates. Must be distinct.
    bounds : tuple[float, float, float, float]
        Bounding rectangle (minx, miny, maxx, maxy) containing all points.

    Returns
    -------
    list[shapely.Polygon]
        List of Voronoi cell polygons, one per input point, in the same order.
    """
    if not points:
        return []

    multipoint = MultiPoint(points)
    minx, miny, maxx, maxy = bounds
    envelope = box(minx, miny, maxx, maxy)

    # voronoi_polygons returns a GeometryCollection of Polygons in the same order as the input points
    voronoi = voronoi_polygons(multipoint, envelope=envelope)

    return list(voronoi.geoms)