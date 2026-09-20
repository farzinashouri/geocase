```python
from shapely.geometry import Point


def tag_points(points, polygons):
    results = []
    for x, y in points:
        pt = Point(x, y)
        match = None
        for index, polygon in enumerate(polygons):
            if polygon.contains(pt) or polygon.boundary.contains(pt):
                match = index
                break
        results.append(match)
    return results
```