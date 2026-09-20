"""Compute the intersection of two 2D line segments."""

from shapely.geometry import LineString


def segment_intersection(a, b):
    """Return the intersection of two line segments.

    Each of `a` and `b` is a segment ((x1, y1), (x2, y2)).

    Returns:
        None if the segments share no point.
        (x, y) if they share exactly one point.
        ((xa, ya), (xb, yb)) if they share a continuous sub-segment.
    """
    line_a = LineString(a)
    line_b = LineString(b)

    inter = line_a.intersection(line_b)

    if inter.is_empty:
        return None

    if inter.geom_type == "Point":
        return (inter.x, inter.y)

    if inter.geom_type == "LineString":
        coords = list(inter.coords)
        return (tuple(coords[0]), tuple(coords[-1]))

    raise ValueError(f"Unexpected intersection geometry: {inter.geom_type}")