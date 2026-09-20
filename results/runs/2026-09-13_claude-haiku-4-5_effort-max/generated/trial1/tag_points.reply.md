```python
from shapely.geometry import Point

def tag_points(points, polygons):
    result = []
    for x, y in points:
        point = Point(x, y)
        found = None
        for i, polygon in enumerate(polygons):
            if polygon.contains(point):
                found = i
                break
        result.append(found)
    return result
```