```python
from shapely.geometry import Point
from shapely.prepared import prep


def tag_points(points, polygons):
    prepared_polygons = [prep(polygon) for polygon in polygons]

    results = []
    for x, y in points:
        point = Point(x, y)
        match = None
        for index, (polygon, prepared) in enumerate(zip(polygons, prepared_polygons)):
            if prepared.covers(point) or polygon.covers(point):
                match = index
                break
        results.append(match)
    return results
```