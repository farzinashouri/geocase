"""Remove duplicate geometries from a list, preserving order of first occurrence."""

from shapely.geometry.base import BaseGeometry


def dedupe_geoms(geoms):
    """Return a new list with duplicate geometries removed.

    Two geometries are considered duplicates when they describe the same
    set of points in the plane, regardless of coordinate ordering (e.g. a
    ring traced from a different starting vertex or in the opposite
    winding direction). Order of first occurrence is preserved.
    """
    seen = set()
    result = []
    for geom in geoms:
        if not isinstance(geom, BaseGeometry):
            raise TypeError(f"expected a shapely geometry, got {type(geom)!r}")
        key = geom.normalize().wkb
        if key not in seen:
            seen.add(key)
            result.append(geom)
    return result