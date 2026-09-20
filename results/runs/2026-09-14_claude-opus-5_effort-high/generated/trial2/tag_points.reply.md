```python
"""Point-in-polygon tagging for planar, non-overlapping polygon sets.

Given points and polygons in a shared planar coordinate system, assign each
point the index of the polygon that contains it. Boundaries count as inside,
so polygons that share an edge both "contain" a point lying on that edge; the
smallest such index wins.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely.geometry.base import BaseGeometry

__all__ = ["tag_points"]


def tag_points(
    points: Iterable[Tuple[float, float]],
    polygons: Sequence[BaseGeometry],
) -> List[Optional[int]]:
    """Tag each point with the index of the polygon covering it.

    Parameters
    ----------
    points:
        Iterable of ``(x, y)`` coordinate pairs.
    polygons:
        Sequence of shapely ``Polygon`` objects in the same planar CRS as the
        points. Interiors are assumed disjoint; shared boundaries are allowed.

    Returns
    -------
    list
        One entry per input point, in input order: the index into ``polygons``
        of the covering polygon (boundary included), or ``None`` if the point
        lies in no polygon. Points on a boundary shared by several polygons get
        the smallest matching index.
    """
    coords = np.asarray(list(points), dtype=float)
    if coords.size == 0:
        # Distinguish "no points" from a genuinely malformed array.
        if coords.ndim == 2 and coords.shape[1] not in (0, 2):
            raise ValueError("points must be (x, y) pairs")
        return []
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError("points must be (x, y) pairs")

    n_points = coords.shape[0]
    result: List[Optional[int]] = [None] * n_points

    polygons = list(polygons)
    if not polygons:
        return result

    pts = shapely.points(coords)
    tree = shapely.STRtree(polygons)

    # For a point, `intersects` is equivalent to `covers`: it is true exactly
    # when the point lies in the polygon's interior or on its boundary.
    point_idx, poly_idx = tree.query(pts, predicate="intersects")
    if point_idx.size == 0:
        return result

    # Write matches in descending polygon order so the smallest index lands
    # last and wins for points sitting on a shared boundary.
    order = np.argsort(poly_idx, kind="stable")[::-1]
    for i, j in zip(point_idx[order].tolist(), poly_idx[order].tolist()):
        result[i] = j

    return result
```