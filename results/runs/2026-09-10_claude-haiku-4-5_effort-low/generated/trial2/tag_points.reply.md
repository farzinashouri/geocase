```python
from shapely.geometry import Point

def tag_points(points, polygons):
    result = []
    for point_tuple in points:
        point = Point(point_tuple)
        tagged = None
        for i, polygon in enumerate(polygons):
            if polygon.intersects(point):
                tagged = i
                break
        result.append(tagged)
    return result
```