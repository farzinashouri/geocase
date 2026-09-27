"""Compute the geometric intersection of two 2D line segments.

Importing this module has no side effects.
"""

from shapely.geometry import LineString, Point


def segment_intersection(a, b):
    """Intersect two 2D line segments.

    Each segment is given as ``((x1, y1), (x2, y2))`` with float
    coordinates in a planar system.

    Returns:
        - ``None`` if the segments share no point,
        - ``(x, y)`` if they share exactly one point,
        - ``((xa, ya), (xb, yb))`` if they share more than one point
          (a collinear overlap), giving the endpoints of the shared
          portion.
    """
    seg_a = LineString([tuple(a[0]), tuple(a[1])])
    seg_b = LineString([tuple(b[0]), tuple(b[1])])

    result = seg_a.intersection(seg_b)

    if result.is_empty:
        return None

    geom_type = result.geom_type

    if geom_type == "Point":
        return (result.x, result.y)

    if geom_type == "LineString":
        coords = list(result.coords)
        start = coords[0]
        end = coords[-1]
        if start == end:
            return (start[0], start[1])
        return ((start[0], start[1]), (end[0], end[1]))

    # Degenerate segments (zero length) or unusual configurations may
    # yield a MultiPoint / GeometryCollection. Reduce to the common
    # points; if everything collapses to a single location return a
    # point, otherwise return the extent of the shared geometry.
    points = []
    geoms = getattr(result, "geoms", [result])
    for g in geoms:
        if g.is_empty:
            continue
        if g.geom_type == "Point":
            points.append((g.x, g.y))
        else:
            c = list(g.coords)
            points.append((c[0][0], c[0][1]))
            points.append((c[-1][0], c[-1][1]))

    if not points:
        return None

    unique = list(dict.fromkeys(points))
    if len(unique) == 1:
        return unique[0]

    xs = [p[0] for p in unique]
    ys = [p[1] for p in unique]
    return ((min(xs), min(ys)), (max(xs), max(ys)))