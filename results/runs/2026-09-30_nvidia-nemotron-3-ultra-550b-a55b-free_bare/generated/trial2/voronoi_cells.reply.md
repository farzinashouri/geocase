```python
"""
Voronoi cell computation clipped to a bounding rectangle.

This module provides a function `voronoi_cells` that computes the Voronoi
diagram for a set of planar points and clips the cells to a given
rectangular bounds. It uses Shapely's `voronoi_polygons` which handles
the clipping via the `extend_to` parameter.
"""

from shapely.geometry import Point, box
from shapely.ops import voronoi_polygons


def voronoi_cells(points, bounds):
    """
    Compute Voronoi cells for a set of points clipped to a rectangular bounds.

    Parameters
    ----------
    points : list[tuple[float, float]]
        List of N distinct (x, y) coordinates in a planar coordinate system.
    bounds : tuple[float, float, float, float]
        Rectangle (minx, miny, maxx, maxy) that contains all points.

    Returns
    -------
    list[shapely.Polygon]
        List of N polygons where the i-th polygon is the region of the
        rectangle closer to points[i] than to any other point.
    """
    # Convert input points to Shapely Point geometries
    geom_points = [Point(x, y) for x, y in points]

    # Create the bounding box polygon from the bounds
    minx, miny, maxx, maxy = bounds
    envelope = box(minx, miny, maxx, maxy)

    # Compute Voronoi polygons clipped to the envelope.
    # The result is a GeometryCollection with one polygon per input point,
    # in the same order as the input points.
    voronoi = voronoi_polygons(geom_points, extend_to=envelope)

    # Extract individual polygons as a list
    return list(voronoi.geoms)
```