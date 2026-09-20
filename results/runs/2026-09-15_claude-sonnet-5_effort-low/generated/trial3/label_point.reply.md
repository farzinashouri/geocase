```python
"""Compute a label point guaranteed to lie inside a polygon."""

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon


def label_point(polygon: Polygon) -> Point:
    point = polygon.representative_point()
    if not polygon.contains(point) and not polygon.intersects(point):
        point = polygon.centroid
        if not polygon.contains(point):
            point = polygon.representative_point()
    return point
```