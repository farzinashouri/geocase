"""Compute the geometric intersection of two 2D line segments.

The intersection of two straight line segments is always one of:
  * empty              -> ``None``
  * a single point     -> ``(x, y)``
  * a shared sub-segment (collinear overlap) -> ``((xa, ya), (xb, yb))``

Importing this module has no side effects.
"""

from shapely.geometry import LineString, Point


def _as_geometry(seg):
    """Build a shapely geometry from a segment.

    A zero-length segment (both endpoints equal) is a degenerate case; we
    represent it as a Point so intersections still behave sensibly.
    """
    (x1, y1), (x2, y2) = seg
    p1 = (float(x1), float(y1))
    p2 = (float(x2), float(y2))
    if p1 == p2:
        return Point(p1)
    return LineString([p1, p2])


def segment_intersection(a, b):
    """Return the intersection of segments ``a`` and ``b``.

    Each argument is ``((x1, y1), (x2, y2))``.  Returns ``None`` for no
    common point, ``(x, y)`` for exactly one common point, or
    ``((xa, ya), (xb, yb))`` for a shared collinear sub-segment.
    """
    geom_a = _as_geometry(a)
    geom_b = _as_geometry(b)

    result = geom_a.intersection(geom_b)

    if result.is_empty:
        return None

    geom_type = result.geom_type

    if geom_type == "Point":
        return (result.x, result.y)

    if geom_type == "LineString":
        coords = list(result.coords)
        # A collinear overlap is a two-point LineString.  If it has
        # collapsed to a single distinct coordinate, report a point.
        start = coords[0]
        end = coords[-1]
        if start == end:
            return (start[0], start[1])
        return ((start[0], start[1]), (end[0], end[1]))

    # Defensive fallback: any other geometry (e.g. a GeometryCollection or
    # MultiPoint produced by numerical edge cases) is reduced to a single
    # point if it collapses to one, otherwise to its bounding endpoints.
    coords = _flatten_coords(result)
    unique = []
    for c in coords:
        if c not in unique:
            unique.append(c)
    if len(unique) == 1:
        return (unique[0][0], unique[0][1])
    minx, miny, maxx, maxy = result.bounds
    return ((minx, miny), (maxx, maxy))


def _flatten_coords(geom):
    """Yield all coordinate tuples contained in an arbitrary geometry."""
    coords = []
    if hasattr(geom, "geoms"):
        for part in geom.geoms:
            coords.extend(_flatten_coords(part))
    else:
        coords.extend(tuple(c) for c in geom.coords)
    return coords