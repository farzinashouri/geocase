from shapely.geometry import Point, box
from shapely.ops import voronoi_diagram

def voronoi_cells(points, bounds):
    """
    Compute Voronoi cells for a set of points clipped to a rectangular bounds.

    Parameters
    ----------
    points : list[tuple[float, float]]
        List of (x, y) coordinates. All points must be distinct.
    bounds : tuple[float, float, float, float]
        Rectangle (minx, miny, maxx, maxy) containing all points.

    Returns
    -------
    list[shapely.Polygon]
        List of Voronoi cell polygons, one per input point, in the same order.
    """
    # Convert input points to shapely Point geometries
    geom_points = [Point(x, y) for x, y in points]

    # Create the bounding rectangle as a shapely Polygon
    minx, miny, maxx, maxy = bounds
    bounds_poly = box(minx, miny, maxx, maxy)

    # Compute the Voronoi diagram extended/clipped to the bounds rectangle
    voronoi = voronoi_diagram(geom_points, extend_to=bounds_poly)

    # Extract the cells (they are ordered to match the input points)
    cells = [cell.intersection(bounds_poly) for cell in voronoi.geoms]

    # Sanity check: we should have exactly one cell per input point
    if len(cells) != len(points):
        raise ValueError("Voronoi diagram did not produce a cell for each point.")

    return cells