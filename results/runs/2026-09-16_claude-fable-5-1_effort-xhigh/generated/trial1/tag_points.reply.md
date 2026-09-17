Verification runs were declined by the permission policy, so the module below is delivered based on shapely 2.x semantics: `STRtree.query` with the `intersects` predicate is the closed-set test (interior or boundary), and the smallest polygon index per point is selected after a lexicographic sort.

```python
"""Assign planar points to the polygons that contain them.

The only public entry point is :func:`tag_points`.  Importing this module has
no side effects.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely import STRtree
from shapely.geometry.base import BaseGeometry

__all__ = ["tag_points"]


def tag_points(
    points: Iterable[Tuple[float, float]],
    polygons: Sequence[BaseGeometry],
) -> List[Optional[int]]:
    """Return, for each point, the index of the polygon containing it.

    Parameters
    ----------
    points
        Iterable of ``(x, y)`` pairs in the same planar coordinate system as
        ``polygons``.
    polygons
        Sequence of shapely polygons.  Their interiors must not overlap, but
        they may share boundaries.

    Returns
    -------
    list
        Exactly one entry per input point, in input order.  Each entry is the
        index of the polygon whose closure (interior or boundary) contains the
        point, or ``None`` if no polygon does.  A point lying on a boundary
        shared by several polygons maps to the smallest such index.
    """
    points = list(points)
    polygons = list(polygons)
    n_points = len(points)
    n_polys = len(polygons)

    result: List[Optional[int]] = [None] * n_points
    if n_points == 0 or n_polys == 0:
        return result

    coords = np.array([(p[0], p[1]) for p in points], dtype=float).reshape(n_points, 2)
    point_geoms = shapely.points(coords)

    # ``intersects`` is the closed-set test: true for interior *and* boundary,
    # so points exactly on an edge or vertex are counted as contained.
    # ``None`` and empty polygons are ignored by the tree and never matched.
    tree = STRtree(polygons)
    point_idx, poly_idx = tree.query(point_geoms, predicate="intersects")
    if point_idx.size == 0:
        return result

    # Sort matches by point index, then polygon index, and keep the first
    # (smallest polygon index) match per point.  This resolves ties for
    # points on boundaries shared by several polygons.
    order = np.lexsort((poly_idx, point_idx))
    point_sorted = point_idx[order]
    poly_sorted = poly_idx[order]
    first_points, first_pos = np.unique(point_sorted, return_index=True)

    for p, q in zip(first_points.tolist(), poly_sorted[first_pos].tolist()):
        result[p] = q
    return result
```