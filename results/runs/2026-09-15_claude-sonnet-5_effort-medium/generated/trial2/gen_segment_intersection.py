"""Compute the intersection of two 2D line segments."""

from shapely.geometry import LineString, Point


def segment_intersection(a, b):
    """Return the intersection of two segments ``a`` and ``b``.

    Each segment is ``((x1, y1), (x2, y2))``. Returns ``None`` if the
    segments share no point, a point ``(x, y)`` if they share exactly one
    point, or a segment ``((xa, ya), (xb, yb))`` if they overlap along a
    line.
    """
    line_a = LineString(a)
    line_b = LineString(b)

    inter = line_a.intersection(line_b)

    if inter.is_empty:
        return None

    if isinstance(inter, Point):
        return (inter.x, inter.y)

    coords = list(inter.coords)
    start = coords[0]
    end = coords[-1]

    if Point(start).equals(Point(end)):
        return (start[0], start[1])

    return ((start[0], start[1]), (end[0], end[1]))