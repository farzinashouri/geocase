```python
from shapely.geometry import Point


def tag_points(points, polygons):
    result = []
    for point in points:
        p = Point(point)
        found = None
        for i, polygon in enumerate(polygons):
            if polygon.contains(p) or polygon.boundary.contains(p):
                found = i
                break
        result.append(found)
    return result
```