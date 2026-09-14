```python
from shapely.geometry import Point


def tag_points(points, polygons):
    """Tag each point with the index of its containing polygon."""
    result = []
    for x, y in points:
        point = Point(x, y)
        for i, polygon in enumerate(polygons):
            if polygon.covers(point):
                result.append(i)
                break
        else:
            result.append(None)
    return result
```