```python
def dedupe_geoms(geoms):
    """
    Return a new list of geometries with duplicates removed, preserving the order of first occurrences.

    Two geometries are considered duplicates if they describe exactly the same set of points
    in the plane (i.e., they are spatially equal), even if their coordinate sequences differ
    (e.g., different starting vertex or winding order).

    Parameters
    ----------
    geoms : list of shapely.geometry.BaseGeometry
        Input geometries.

    Returns
    -------
    list of shapely.geometry.BaseGeometry
        List with duplicates removed.
    """
    unique = []
    for geom in geoms:
        # Check if geom is spatially equal to any already kept geometry
        if not any(geom.equals(u) for u in unique):
            unique.append(geom)
    return unique
```