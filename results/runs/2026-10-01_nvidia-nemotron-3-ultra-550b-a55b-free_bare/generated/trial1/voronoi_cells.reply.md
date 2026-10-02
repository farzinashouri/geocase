```python
from shapely.geometry import Point, MultiPoint, box
from shapely.ops import voronoi_diagram

def voronoi_cells(points, bounds):
    """
    Compute Voronoi cells for a set of points clipped to a bounding rectangle.

    Parameters
    ----------
    points : list[tuple[float, float]]
        List of (x, y) coordinates. All points must be distinct.
    bounds : tuple[float, float, float, float]
        Bounding rectangle as (minx, miny, maxx, maxy) containing all points.

    Returns
    -------
    list[shapely.Polygon]
        List of polygons where the i-th polygon is the region of the rectangle
        closer to points[i] than to any other point.
    """
    if not points:
        return []

    # Create a MultiPoint geometry from the input points
    multipoint = MultiPoint(points)

    # Create the clipping envelope as a Polygon
    envelope = box(*bounds)

    # Compute the Voronoi diagram clipped to the envelope
    voronoi = voronoi_diagram(multipoint, envelope=envelope)

    # Extract the individual polygons (cells)
    cells = list(voronoi.geoms)

    # Match each input point to its Voronoi cell by containment.
    # Since points are distinct and the cells partition the envelope,
    # each point lies in exactly one cell.
    result = []
    for pt in points:
        point_geom = Point(pt)
        for cell in cells:
            if cell.contains(point_geom):
                result.append(cell)
                break
        else:
            # Fallback: if a point lies exactly on a boundary, contains may fail.
            # Use intersects (should match exactly one cell).
            for cell in cells:
                if cell.intersects(point_geom):
                    result.append(cell)
                    break

    return result
```