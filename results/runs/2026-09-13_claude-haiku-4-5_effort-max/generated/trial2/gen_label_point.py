from shapely.geometry import Polygon, Point


def label_point(polygon: Polygon) -> Point:
    """Return a Point inside the polygon suitable for placing a text label."""
    return polygon.representative_point()