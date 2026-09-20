from shapely.geometry import Point


def tag_points(points, polygons):
    shapely_points = [Point(x, y) for x, y in points]
    results = []
    for pt in shapely_points:
        match = None
        for idx, polygon in enumerate(polygons):
            if polygon.covers(pt):
                match = idx
                break
        results.append(match)
    return results