"""
A small utility module for generating a suitable label point inside a Shapely Polygon.

The main function, `label_point`, returns a Shapely `Point` that lies inside the given
polygon. This point can be used as a reference location for drawing text labels
on maps or visualizations.

Dependencies
------------
- shapely 2.1
"""

from __future__ import annotations

from typing import Any

from shapely.geometry import Polygon, Point


def label_point(polygon: Polygon) -> Point:
    """
    Return a point inside the given polygon suitable for placing a text label.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        The polygon for which a label point is required.

    Returns
    -------
    shapely.geometry.Point
        A point guaranteed to lie inside the polygon.

    Raises
    ------
    TypeError
        If the input is not a shapely Polygon.
    ValueError
        If the polygon is empty or has no interior.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"Expected shapely.geometry.Polygon, got {type(polygon).__name__}")

    if polygon.is_empty:
        raise ValueError("Cannot generate a label point for an empty polygon")

    # `representative_point` returns a point that is guaranteed to be inside the polygon.
    return polygon.representative_point()


__all__ = ["label_point"]