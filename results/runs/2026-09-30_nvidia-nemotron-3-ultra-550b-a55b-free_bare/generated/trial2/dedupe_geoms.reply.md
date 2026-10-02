```python
from shapely.geometry import base

def dedupe_geoms(geoms):
    """
    Return a new list of geometries with duplicates removed, preserving order.

    Two geometries are considered duplicates if they are geometrically equal,
    i.e., they represent the same set of points in the plane. This includes
    cases where coordinate sequences differ (e.g., different starting vertex
    or opposite winding order).

    Parameters
    ----------
    geoms : list[shapely.geometry.base.BaseGeometry]
        List of Shapely geometry objects.

    Returns
    -------
    list[shapely.geometry.base.BaseGeometry]
        List containing the first occurrence of each unique geometry.
    """
    unique = []
    for geom in geoms:
        # Check if geom is geometrically equal to any already kept geometry
        if not any(geom.equals(u) for u in unique):
            unique.append(geom)
    return unique
```