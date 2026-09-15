"""Compute a label point guaranteed to lie inside a polygon."""

from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import Polygon


def label_point(polygon: Polygon) -> Point:
    """Return a Point inside ``polygon`` suitable for placing a text label.

    Uses the polygon's pole of inaccessibility (via shapely's
    ``maximum_inscribed_circle``), which maximizes distance from the
    boundary and therefore gives a visually central, interior point even
    for concave or oddly shaped polygons. Falls back to ``representative_point``
    if that fails for any reason.
    """
    try:
        circle = polygon.maximum_inscribed_circle()
        center = Point(circle.coords[0])
        if polygon.contains(center):
            return center
    except Exception:
        pass

    return polygon.representative_point()