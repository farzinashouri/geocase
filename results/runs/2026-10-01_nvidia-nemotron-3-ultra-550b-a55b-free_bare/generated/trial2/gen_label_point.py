from shapely.geometry import Polygon
from shapely.ops import polylabel

def label_point(polygon):
    """
    Return a point inside the given polygon suitable for placing a text label.
    Uses the pole of inaccessibility (polylabel) to find the point farthest from
    the polygon boundary, which is a good candidate for label placement.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        The polygon to label. Can be in any coordinate system.

    Returns
    -------
    shapely.geometry.Point
        A point guaranteed to lie inside the polygon (including interior rings).

    Raises
    ------
    ValueError
        If the input is not a Polygon or is empty.
    """
    if not isinstance(polygon, Polygon):
        raise ValueError("Input must be a shapely Polygon")
    if polygon.is_empty:
        raise ValueError("Polygon is empty")
    return polylabel(polygon)