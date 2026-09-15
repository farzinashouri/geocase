"""Compute a point suitable for labeling a shapely Polygon."""

from shapely.geometry import Polygon, Point


def label_point(polygon: Polygon) -> Point:
    point = polygon.representative_point()
    if polygon.contains(point):
        return point

    centroid = polygon.centroid
    if polygon.contains(centroid):
        return centroid

    return polygon.representative_point()