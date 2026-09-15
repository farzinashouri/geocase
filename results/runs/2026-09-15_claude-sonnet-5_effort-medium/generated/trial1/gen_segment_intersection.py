"""Segment-segment intersection in the plane."""

from shapely.geometry import LineString


def segment_intersection(a, b):
    line_a = LineString(a)
    line_b = LineString(b)

    result = line_a.intersection(line_b)

    if result.is_empty:
        return None

    if result.geom_type == "Point":
        return (result.x, result.y)

    if result.geom_type == "LineString":
        coords = list(result.coords)
        return ((coords[0][0], coords[0][1]), (coords[-1][0], coords[-1][1]))

    for geom in getattr(result, "geoms", []):
        if geom.geom_type == "LineString":
            coords = list(geom.coords)
            return ((coords[0][0], coords[0][1]), (coords[-1][0], coords[-1][1]))

    for geom in getattr(result, "geoms", []):
        if geom.geom_type == "Point":
            return (geom.x, geom.y)

    return None