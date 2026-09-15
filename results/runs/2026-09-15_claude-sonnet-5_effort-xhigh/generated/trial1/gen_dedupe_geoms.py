"""Deduplicate shapely geometries that describe the same set of points."""

import shapely


def dedupe_geoms(geoms):
    """Return geoms with duplicates removed, keeping first occurrence and order.

    Two geometries are considered duplicates when they describe the same set
    of points in the plane, regardless of coordinate ordering (e.g. a ring
    starting at a different vertex, or traversed in the opposite direction).
    This is achieved by comparing each geometry's GEOS-normalized canonical
    form rather than its raw coordinate sequence.
    """
    seen = set()
    result = []
    for geom in geoms:
        key = shapely.to_wkb(shapely.normalize(geom))
        if key not in seen:
            seen.add(key)
            result.append(geom)
    return result