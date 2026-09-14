```python
from shapely.geometry import Point


def tag_points(points, polygons):
    result = []
    for x, y in points:
        point = Point(x, y)
        containing_indices = []
        for i, poly in enumerate(polygons):
            if poly.covers(point):
                containing_indices.append(i)
        
        if containing_indices:
            result.append(min(containing_indices))
        else:
            result.append(None)
    
    return result
```