from shapely.geometry import Polygon, Point

def label_point(polygon: Polygon) -> Point:
    """
    Return a point guaranteed to lie inside the given polygon, suitable for placing a text label.

    This uses Shapely's `representative_point()` method (GEOS's ST_PointOnSurface),
    which returns a point that is guaranteed to be within the polygon.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        The polygon for which to compute a label point. Can be in any coordinate system.

    Returns
    -------
    shapely.geometry.Point
        A point inside the polygon.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError("Expected a shapely Polygon object.")
    return polygon.representative_point()