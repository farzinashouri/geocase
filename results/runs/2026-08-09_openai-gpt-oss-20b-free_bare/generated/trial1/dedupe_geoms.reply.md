```python
"""
Utility module for deduplicating shapely geometries.
"""

import shapely


def dedupe_geoms(geoms):
    """
    Return a new list of shapely geometries with duplicates removed.
    Two geometries are considered duplicates if they are topologically equal,
    i.e. they describe exactly the same set of points in the plane, regardless
    of coordinate ordering or orientation (for rings). The first occurrence
    of each unique geometry is preserved, and the original order is maintained.

    Parameters
    ----------
    geoms : list
        A list of shapely geometry objects.

    Returns
    -------
    list
        A new list containing only the first occurrence of each unique geometry.
    """
    unique = []
    for g in geoms:
        if not any(g.equals(u) for u in unique):
            unique.append(g)
    return unique
```