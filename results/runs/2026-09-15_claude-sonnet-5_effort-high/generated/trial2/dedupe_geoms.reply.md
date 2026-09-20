```python
"""Remove duplicate shapely geometries, treating geometries as equal when they
describe the same set of points regardless of vertex order or ring direction.
"""


def dedupe_geoms(geoms):
    """Return a new list with duplicate geometries removed, preserving order.

    Two geometries are considered duplicates when they represent the same set
    of points in the plane, even if their coordinate sequences differ (e.g.
    the same ring traced from a different starting vertex or in the opposite
    winding direction).

    Args:
        geoms: A list of shapely geometries.

    Returns:
        A new list containing the first occurrence of each distinct geometry.
    """
    result = []
    seen_keys = set()
    for geom in geoms:
        # normalize() puts a geometry into a canonical form: it fixes ring
        # winding direction and picks a canonical starting vertex, so two
        # geometries covering the same points normalize to identical WKB
        # even if their original coordinate sequences differ.
        key = geom.normalize().wkb_hex
        if key not in seen_keys:
            seen_keys.add(key)
            result.append(geom)
    return result
```