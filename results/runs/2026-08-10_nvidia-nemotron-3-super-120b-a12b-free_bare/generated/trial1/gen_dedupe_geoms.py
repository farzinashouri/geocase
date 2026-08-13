from shapely.geometry import BaseGeometry
from typing import Iterable, List

def dedupe_geoms(geoms: Iterable[BaseGeometry]) -> List[BaseGeometry]:
    """Return a list with duplicate geometries removed, preserving first occurrence order.

    Two geometries are considered duplicates when they describe exactly the same set of
    points in the plane (i.e., ``geom1.equals(geom2)`` is True), regardless of vertex
    ordering, starting point, or direction.

    Parameters
    ----------
    geoms : iterable of shapely geometries
        The input geometries to deduplicate.

    Returns
    -------
    list of shapely geometries
        A new list containing the first occurrence of each unique geometry.
    """
    unique: List[BaseGeometry] = []
    for geom in geoms:
        # Check against already‑kept geometries using topological equality.
        if not any(geom.equals(u) for u in unique):
            unique.append(geom)
    return unique