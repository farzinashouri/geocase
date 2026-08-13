```python
# tag_points.py
"""
Utility module for tagging points with the index of the polygon that contains them.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree


def tag_points(
    points: Iterable[Tuple[float, float]],
    polygons: Iterable[Polygon],
) -> List[Optional[int]]:
    """
    Tag each point with the index of the polygon that contains it.

    Parameters
    ----------
    points : Iterable[Tuple[float, float]]
        A sequence of (x, y) tuples representing points.
    polygons : Iterable[Polygon]
        A sequence of Shapely Polygon objects.  Polygons may share boundaries
        but their interiors do not overlap.

    Returns
    -------
    List[Optional[int]]
        A list of the same length as ``points``.  Each element is the index
        of the polygon that contains the corresponding point, or ``None`` if
        the point lies in no polygon.  Points on a shared boundary are
        assigned to the polygon with the smallest index among those that
        cover the point.

    Notes
    -----
    * A point lying exactly on a polygon's boundary counts as contained
      (the ``covers`` method is used).
    * The function is efficient for large numbers of points and polygons
      thanks to a spatial index (STRtree).
    """
    # Convert inputs to lists for repeated indexing
    point_list = list(points)
    polygon_list = list(polygons)

    # Build a spatial index for the polygons
    tree = STRtree(polygon_list)

    # Map each geometry to its index for quick lookup
    geom_to_index = {id(poly): idx for idx, poly in enumerate(polygon_list)}

    result: List[Optional[int]] = []

    for x, y in point_list:
        pt = Point(x, y)
        # Query candidate polygons whose bounding boxes intersect the point
        candidates = tree.query(pt)
        min_index: Optional[int] = None

        for candidate in candidates:
            # Use covers to include boundary points
            if candidate.covers(pt):
                idx = geom_to_index[id(candidate)]
                if min_index is None or idx < min_index:
                    min_index = idx

        result.append(min_index)

    return result
```