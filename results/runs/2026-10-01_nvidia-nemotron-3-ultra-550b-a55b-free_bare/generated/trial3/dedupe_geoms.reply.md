```python
"""
Module for deduplicating a list of Shapely geometries based on geometric equality.
"""

from __future__ import annotations

from typing import List, Any

try:
    from shapely.geometry.base import BaseGeometry
except ImportError:
    # For type checking only; shapely is required at runtime.
    BaseGeometry = Any


def dedupe_geoms(geoms: List[BaseGeometry]) -> List[BaseGeometry]:
    """
    Return a new list of geometries with duplicates removed, preserving the order
    of first occurrences.

    Two geometries are considered duplicates if they are spatially equal
    (i.e., they describe exactly the same set of points in the plane), even if
    their coordinate sequences differ (e.g., different starting vertex or ring
    direction).

    Parameters
    ----------
    geoms : list of shapely.geometry.BaseGeometry
        Input geometries.

    Returns
    -------
    list of shapely.geometry.BaseGeometry
        Geometries with duplicates removed, in the order of their first appearance.
    """
    unique: List[BaseGeometry] = []
    for geom in geoms:
        # Check if this geometry is equal to any already kept geometry.
        # shapely's `equals` method implements geometric equality.
        if not any(geom.equals(u) for u in unique):
            unique.append(geom)
    return unique
```