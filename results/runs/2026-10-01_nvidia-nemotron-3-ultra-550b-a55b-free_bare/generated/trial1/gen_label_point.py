"""
Module for computing a suitable label point inside a polygon.
"""

from shapely.geometry import Polygon, Point


def label_point(polygon: Polygon) -> Point:
    """
    Return a point inside the given polygon suitable for placing a text label.

    The function first tries the polygon's centroid. If the centroid lies
    inside the polygon (i.e., not in a hole or outside for non-convex shapes),
    it is returned. Otherwise, a guaranteed interior point is obtained via
    `representative_point()`.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        The polygon for which to compute a label point. Can be in any coordinate system.

    Returns
    -------
    shapely.geometry.Point
        A point guaranteed to lie in the interior of the polygon.
    """
    centroid = polygon.centroid
    if polygon.contains(centroid):
        return centroid
    return polygon.representative_point()