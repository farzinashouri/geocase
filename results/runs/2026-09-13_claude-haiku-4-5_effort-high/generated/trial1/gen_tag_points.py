from shapely.geometry import Point


def tag_points(points, polygons):
    """
    Tag each point with the index of its containing polygon.
    
    Returns the polygon index for each point in input order, where a point
    on a shared boundary gets the smallest polygon index, or None if the
    point is in no polygon.
    """
    result = []
    for x, y in points:
        point = Point(x, y)
        containing_indices = [i for i, poly in enumerate(polygons) if poly.contains(point)]
        result.append(min(containing_indices) if containing_indices else None)
    return result