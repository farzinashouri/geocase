```python
from __future__ import annotations

from typing import List, Tuple, Optional

from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree


def tag_points(
    points: List[Tuple[float, float]],
    polygons: List[Polygon],
) -> List[Optional[int]]:
    """
    Tag each point with the index of the polygon that contains it.

    Parameters
    ----------
    points : list of (x, y) tuples
        Points to be tested.
    polygons : list of shapely.geometry.Polygon
        Polygons that may share boundaries but have non‑overlapping interiors.

    Returns
    -------
    list of int or None
        For each point, the index of the polygon that contains it (including
        boundary points). If a point lies on a shared boundary, the smallest
        polygon index is returned. If the point is outside all polygons,
        None is returned.
    """
    # Build a spatial index for fast candidate lookup
    tree = STRtree(polygons)
    # Map geometry id to its original index
    id_to_index = {id(poly): idx for idx, poly in enumerate(polygons)}

    result: List[Optional[int]] = []

    for x, y in points:
        pt = Point(x, y)
        # Find candidate polygons that intersect the point's envelope
        candidates = tree.query(pt)
        best_idx: Optional[int] = None

        for poly in candidates:
            if poly.covers(pt):
                idx = id_to_index[id(poly)]
                if best_idx is None or idx < best_idx:
                    best_idx = idx

        result.append(best_idx)

    return result
```