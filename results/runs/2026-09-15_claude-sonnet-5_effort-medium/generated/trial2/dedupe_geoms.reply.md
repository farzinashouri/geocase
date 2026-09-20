```python
"""Deduplicate shapely geometries that represent the same set of points."""

from shapely.geometry.base import BaseGeometry


def dedupe_geoms(geoms):
    """Return a new list with duplicate geometries removed, keeping first occurrence order.

    Two geometries are considered duplicates when they describe the same set of
    points in the plane, regardless of coordinate ordering, starting vertex, or
    ring direction (e.g. a polygon and its reversed/rotated equivalent).
    """
    result = []
    seen_keys = []

    for geom in geoms:
        key = _geom_key(geom)
        is_duplicate = False
        for seen_geom, seen_key in seen_keys:
            if key == seen_key and geom.equals(seen_geom):
                is_duplicate = True
                break
        if not is_duplicate:
            result.append(geom)
            seen_keys.append((geom, key))

    return result


def _geom_key(geom: BaseGeometry):
    normalized = geom.normalize()
    return (geom.geom_type, normalized.wkb_hex)
```