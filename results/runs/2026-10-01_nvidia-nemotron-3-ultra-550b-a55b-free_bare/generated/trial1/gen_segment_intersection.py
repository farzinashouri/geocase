from shapely.geometry import LineString, Point

def segment_intersection(a, b):
    """
    Compute the intersection of two 2D line segments.

    Parameters
    ----------
    a : ((float, float), (float, float))
        First segment as ((x1, y1), (x2, y2)).
    b : ((float, float), (float, float))
        Second segment as ((x1, y1), (x2, y2)).

    Returns
    -------
    None | (float, float) | ((float, float), (float, float))
        None if no intersection;
        a point (x, y) if they intersect in exactly one point;
        a segment ((xa, ya), (xb, yb)) if they overlap in a segment.
    """
    def _make_geometry(seg):
        (x1, y1), (x2, y2) = seg
        if x1 == x2 and y1 == y2:
            return Point(x1, y1)
        return LineString(seg)

    geom1 = _make_geometry(a)
    geom2 = _make_geometry(b)
    inter = geom1.intersection(geom2)

    if inter.is_empty:
        return None

    if inter.geom_type == 'Point':
        return (inter.x, inter.y)

    if inter.geom_type == 'LineString':
        coords = list(inter.coords)
        if len(coords) >= 2:
            return (tuple(coords[0]), tuple(coords[-1]))
        if len(coords) == 1:
            return tuple(coords[0])
        return None

    # For two simple segments this should not occur, but handle gracefully.
    return None