```python
"""Tag planar points with the index of the polygon that contains them.

The only public entry point is :func:`tag_points`.  Importing this module has
no side effects beyond the imports themselves.
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
    """Return, for each point, the index of the polygon containing it.

    Parameters
    ----------
    points:
        Iterable of ``(x, y)`` tuples in the same planar coordinate system as
        ``polygons``.
    polygons:
        Sequence of shapely ``Polygon`` objects.  Interiors are assumed not to
        overlap, though boundaries may be shared.

    Returns
    -------
    list
        One entry per input point, in input order.  Each entry is the index of
        the containing polygon, or ``None`` if the point lies in no polygon.
        Points on a polygon boundary count as contained; a point on a boundary
        shared by several polygons gets the smallest of those indices.
    """
    polys = list(polygons)
    coords = np.asarray(points, dtype=float)

    # Empty input on either side: nothing can match.
    if coords.size == 0:
        return [] if coords.ndim < 2 or coords.shape[0] == 0 else [None] * coords.shape[0]
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError(
            f"points must be an (n, 2) sequence of (x, y) pairs, got shape {coords.shape}"
        )

    n_points = coords.shape[0]
    if not polys:
        return [None] * n_points

    point_geoms = shapely.points(coords)

    # For a point, `intersects` is exactly "interior or boundary", which is the
    # boundary-inclusive containment we want -- and it is symmetric, so the
    # argument order of the tree predicate cannot bite us.
    tree = shapely.STRtree(polys)
    point_idx, poly_idx = tree.query(point_geoms, predicate="intersects")

    winners = np.full(n_points, -1, dtype=np.int64)
    if point_idx.size:
        # Sort by (point, polygon) so the first row of each point group holds
        # the smallest polygon index -- the tie-break for shared boundaries.
        order = np.lexsort((poly_idx, point_idx))
        point_sorted = point_idx[order]
        poly_sorted = poly_idx[order]
        is_first = np.ones(point_sorted.shape, dtype=bool)
        is_first[1:] = point_sorted[1:] != point_sorted[:-1]
        winners[point_sorted[is_first]] = poly_sorted[is_first]

    return [None if w < 0 else int(w) for w in winners.tolist()]
```