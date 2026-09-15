```python
"""Deduplicate a list of shapely geometries by their point set, ignoring
vertex order, ring start point, and ring direction."""

from shapely.geometry.base import BaseGeometry


def dedupe_geoms(geoms):
    """Return a new list of geometries with duplicates removed.

    The first occurrence of each distinct geometry is kept and the
    original order is preserved. Two geometries are considered duplicates
    if they represent exactly the same set of points in the plane, even
    if their coordinate sequences start at a different vertex or run in
    the opposite direction.
    """
    result = []
    seen_wkb = set()

    for geom in geoms:
        normalized = geom.normalize()
        key = normalized.wkb

        if key in seen_wkb:
            continue

        seen_wkb.add(key)
        result.append(geom)

    return result
```