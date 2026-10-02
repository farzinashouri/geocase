```python
"""Module for deduplicating Shapely geometries based on topological equality."""

from __future__ import annotations

from shapely.geometry.base import BaseGeometry


def dedupe_geoms(geoms: list[BaseGeometry]) -> list[BaseGeometry]:
    """
    Return a new list of geometries with duplicates removed, preserving order.

    Two geometries are considered duplicates if they are topologically equal
    (i.e., they represent the same set of points in the plane), even if their
    coordinate sequences differ (e.g., different starting vertex or ring direction).

    Parameters
    ----------
    geoms : list[BaseGeometry]
        List of Shapely geometries.

    Returns
    -------
    list[BaseGeometry]
        List with duplicates removed, keeping the first occurrence of each.
    """
    unique: list[BaseGeometry] = []
    for geom in geoms:
        # Check if geom is topologically equal to any already kept geometry
        if not any(geom.equals(other) for other in unique):
            unique.append(geom)
    return unique
```