"""Module for computing a label point inside a polygon."""

from shapely.geometry import Polygon, Point


def label_point(polygon: Polygon) -> Point:
    """
    Return a point inside the given polygon suitable for placing a text label.

    The point is the polygon's representative point, which is guaranteed to lie
    within the polygon. This works for polygons in any coordinate system.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        The polygon for which to compute a label point.

    Returns
    -------
    shapely.geometry.Point
        A point inside the polygon.

    Raises
    ------
    TypeError
        If the input is not a shapely Polygon.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError("Input must be a shapely Polygon")

    return polygon.representative_point()