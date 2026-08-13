```python
"""
label_point module

Provides a single function `label_point(polygon)` that returns a point
inside the given Shapely `Polygon`.  The point is suitable for placing
a text label on the polygon.

The implementation uses Shapely's `representative_point`, which
guarantees that the returned point lies within the polygon
(even for concave shapes).  No side effects occur on import.
"""

from __future__ import annotations

from typing import Any

from shapely.geometry import Polygon, Point

__all__ = ["label_point"]


def label_point(polygon: Polygon) -> Point:
    """
    Return a point inside the given polygon suitable for labeling.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        The polygon for which a label point is required.

    Returns
    -------
    shapely.geometry.Point
        A point guaranteed to lie within the polygon.

    Raises
    ------
    TypeError
        If the input is not a shapely Polygon.
    ValueError
        If the polygon is empty or has no interior.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError("polygon must be a shapely.geometry.Polygon instance")

    if polygon.is_empty:
        raise ValueError("Cannot compute a label point for an empty polygon")

    # representative_point() returns a point guaranteed to be inside the polygon
    return polygon.representative_point()
```