```python
"""Deduplicate a list of shapely geometries by geometric equality."""

from shapely.geometry.base import BaseGeometry


def dedupe_geoms(geoms):
    """Return a new list with duplicate geometries removed, preserving order.

    Two geometries are considered duplicates if they describe the same set
    of points in the plane, regardless of coordinate ordering (e.g. a ring
    starting at a different vertex, or wound in the opposite direction).
    """
    result = []
    seen = set()

    for geom in geoms:
        if not isinstance(geom, BaseGeometry):
            raise TypeError(f"Expected a shapely geometry, got {type(geom)!r}")

        key = geom.normalize().wkb_hex

        if key in seen:
            continue

        seen.add(key)
        result.append(geom)

    return result
```