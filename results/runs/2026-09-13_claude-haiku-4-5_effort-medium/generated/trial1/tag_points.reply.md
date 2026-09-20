```python
from shapely.geometry import Point


def tag_points(points, polygons):
    result = []
    for x, y in points:
        point = Point(x, y)
        min_index = None
        for i, polygon in enumerate(polygons):
            if polygon.contains(point):
                if min_index is None or i < min_index:
                    min_index = i
        result.append(min_index)
    return result
```