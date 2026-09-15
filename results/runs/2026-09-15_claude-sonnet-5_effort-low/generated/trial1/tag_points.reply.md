```python
from shapely.geometry import Point


def tag_points(points, polygons):
    result = []
    for x, y in points:
        pt = Point(x, y)
        match = None
        for idx, poly in enumerate(polygons):
            if poly.contains(pt) or poly.boundary.contains(pt):
                match = idx
                break
        result.append(match)
    return result
```