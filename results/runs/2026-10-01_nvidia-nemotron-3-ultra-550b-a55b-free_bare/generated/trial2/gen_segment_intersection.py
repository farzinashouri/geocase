from shapely.geometry import LineString

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
    None or tuple or tuple of tuples
        - None if the segments have no point in common.
        - (x, y) if they have exactly one point in common.
        - ((xa, ya), (xb, yb)) giving the endpoints of the shared portion
          if they have more than one point in common (i.e., are collinear and overlap).
    """
    line_a = LineString(a)
    line_b = LineString(b)

    inter = line_a.intersection(line_b)

    if inter.is_empty:
        return None
    elif inter.geom_type == 'Point':
        return (inter.x, inter.y)
    elif inter.geom_type == 'LineString':
        coords = list(inter.coords)
        # The intersection of two straight segments is a straight segment,
        # so the LineString will have exactly two distinct endpoints.
        # Use the first and last coordinate to be safe.
        return (coords[0], coords[-1])
    else:
        # This should not happen for two LineStrings, but fallback to None.
        return None