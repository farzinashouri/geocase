```python
"""
Module for deduplicating a list of Shapely geometries based on spatial equality.

Two geometries are considered duplicates if they describe exactly the same set of
points in the plane (i.e., they are spatially equal), regardless of differences
in coordinate ordering, starting vertex, or ring direction.
"""

from shapely.geometry import BaseGeometry


def dedupe_geoms(geoms: list[BaseGeometry]) -> list[BaseGeometry]:
    """
    Return a new list with duplicate geometries removed, preserving the order of
    first occurrences.

    Parameters
    ----------
    geoms : list of shapely.geometry.BaseGeometry
        Input geometries. May be any geometry type (Point, LineString, Polygon,
        MultiPolygon, etc.).

    Returns
    -------
    list of shapely.geometry.BaseGeometry
        Geometries from the input with duplicates removed. The first occurrence
        of each spatially unique geometry is kept.
    """
    unique: list[BaseGeometry] = []
    for geom in geoms:
        # Check if this geometry is spatially equal to any already kept geometry.
        # Shapely's `equals` method returns True when two geometries have the
        # same point set, handling different vertex orders and ring directions.
        if not any(geom.equals(u) for u in unique):
            unique.append(geom)
    return unique
```