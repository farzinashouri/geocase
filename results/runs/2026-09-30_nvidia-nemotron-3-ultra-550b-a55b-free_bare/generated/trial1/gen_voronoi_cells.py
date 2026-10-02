from shapely.geometry import Point, box
from shapely.ops import voronoi_diagram

def voronoi_cells(points, bounds):
    """
    Compute Voronoi cells for a set of points clipped to a bounding rectangle.

    Parameters
    ----------
    points : list[tuple[float, float]]
        List of (x, y) coordinates in a planar coordinate system.
    bounds : tuple[float, float, float, float]
        Bounding rectangle (minx, miny, maxx, maxy) that contains all points.

    Returns
    -------
    list[shapely.Polygon]
        List of Voronoi cell polygons, one per input point, in the same order.
        Each polygon represents the part of the rectangle closer to the
        corresponding point than to any other.
    """
    # Convert input points to Shapely Point objects
    shapely_points = [Point(x, y) for x, y in points]

    # Create the clipping rectangle as a Shapely Polygon
    minx, miny, maxx, maxy = bounds
    bounds_poly = box(minx, miny, maxx, maxy)

    # Compute the Voronoi diagram clipped to the bounds rectangle.
    # The `extend_to` parameter ensures the diagram covers exactly the envelope
    # of the provided geometry (the bounds rectangle).
    diagram = voronoi_diagram(shapely_points, extend_to=bounds_poly)

    # The diagram is a GeometryCollection of Polygons ordered to match the input points.
    cells = list(diagram.geoms)

    # Sanity check: we should have one cell per input point.
    if len(cells) != len(points):
        raise RuntimeError(
            f"Voronoi diagram produced {len(cells)} cells for {len(points)} points."
        )

    return cells