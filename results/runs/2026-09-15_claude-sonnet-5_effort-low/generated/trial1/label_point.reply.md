```python
"""Compute a point suitable for labeling a shapely Polygon."""

from shapely.geometry import Polygon, Point


def label_point(polygon: Polygon) -> Point:
    """Return a Point inside `polygon` suitable for placing a text label."""
    point = polygon.representative_point()
    if not polygon.contains(point) and not polygon.intersects(point):
        point = polygon.centroid
        if not polygon.contains(point):
            point = polygon.representative_point()
    return point
```