"""Compute the intersection of two 2D line segments."""

from shapely.geometry import LineString, Point


def _to_geometry(segment):
    (x1, y1), (x2, y2) = segment
    if (x1, y1) == (x2, y2):
        return Point(x1, y1)
    return LineString([(x1, y1), (x2, y2)])


def segment_intersection(a, b):
    geom_a = _to_geometry(a)
    geom_b = _to_geometry(b)
    inter = geom_a.intersection(geom_b)

    if inter.is_empty:
        return None

    if inter.geom_type == "Point":
        return (inter.x, inter.y)

    if inter.geom_type == "LineString":
        coords = list(inter.coords)
        return (tuple(coords[0]), tuple(coords[-1]))

    raise ValueError(f"Unexpected intersection geometry: {inter.geom_type}")