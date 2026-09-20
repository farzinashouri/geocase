from shapely.geometry import Point


def tag_points(points, polygons):
    results = []
    for x, y in points:
        pt = Point(x, y)
        match = None
        for idx, poly in enumerate(polygons):
            if poly.contains(pt) or poly.boundary.contains(pt):
                match = idx
                break
        results.append(match)
    return results