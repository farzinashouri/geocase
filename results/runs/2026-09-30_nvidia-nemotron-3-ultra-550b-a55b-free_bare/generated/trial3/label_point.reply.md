```python
"""Module for computing label points for polygons."""

from shapely.geometry import Polygon, Point


def label_point(polygon: Polygon) -> Point:
    """
    Return a point inside the given polygon suitable for placing a text label.

    This function uses Shapely's `representative_point()` method, which returns
    a point guaranteed to be within the polygon. This is a cheap and robust
    way to obtain an interior point for labeling purposes.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        The polygon for which to compute a label point. Must be a valid, non-empty polygon.

    Returns
    -------
    shapely.geometry.Point
        A point inside the polygon.

    Raises
    ------
    TypeError
        If the input is not a shapely Polygon.
    ValueError
        If the polygon is empty.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(f"Expected a shapely Polygon, got {type(polygon).__name__}")
    if polygon.is_empty:
        raise ValueError("Cannot compute label point for an empty polygon")
    return polygon.representative_point()
```