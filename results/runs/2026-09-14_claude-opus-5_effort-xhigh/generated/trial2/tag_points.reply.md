```python
"""Tag planar points with the index of the polygon that contains them.

Containment is closed: a point lying exactly on a polygon's boundary counts as
contained.  Because the polygons may share edges, a boundary point can match
several polygons; the smallest matching index wins.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely import STRtree

__all__ = ["tag_points"]


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence["shapely.Polygon"],
) -> List[Optional[int]]:
    """Return, for each point, the index of the polygon containing it.

    Parameters
    ----------
    points:
        Sequence of ``(x, y)`` coordinate pairs.
    polygons:
        Sequence of shapely ``Polygon`` objects in the same planar coordinate
        system as ``points``.  Interiors are assumed not to overlap, though
        boundaries may be shared.

    Returns
    -------
    list
        One entry per input point, in input order: the index of the containing
        polygon (boundaries included), or ``None`` if the point lies in no
        polygon.  Points on a shared boundary get the smallest matching index.
    """
    polygons = list(polygons)

    coords = np.asarray(points, dtype="float64")
    if coords.size == 0:
        # Covers both an empty sequence and an empty (0, 2) array.
        return []
    if coords.ndim != 2 or coords.shape[1] < 2:
        raise ValueError(
            "points must be a sequence of (x, y) pairs; "
            f"got an array of shape {coords.shape}"
        )
    coords = coords[:, :2]

    n_points = coords.shape[0]
    result: List[Optional[int]] = [None] * n_points
    if not polygons:
        return result

    # For a zero-dimensional geometry, `intersects` is exactly closed
    # containment: it is true on the interior and on the boundary, and false
    # inside any hole.
    tree = STRtree(polygons)
    point_idx, poly_idx = tree.query(shapely.points(coords), predicate="intersects")
    if poly_idx.size == 0:
        return result

    # Sort by (point, polygon) so that the first row for each point carries the
    # smallest polygon index -- the tie-break for shared boundaries.
    order = np.lexsort((poly_idx, point_idx))
    point_idx = point_idx[order]
    poly_idx = poly_idx[order]

    first_hit = np.empty(point_idx.shape, dtype=bool)
    first_hit[0] = True
    np.not_equal(point_idx[1:], point_idx[:-1], out=first_hit[1:])

    for pi, gi in zip(point_idx[first_hit].tolist(), poly_idx[first_hit].tolist()):
        result[pi] = gi
    return result
```