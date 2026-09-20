```python
"""Tag planar points with the polygon that covers them.

Importing this module has no side effects; :func:`tag_points` is the only
public entry point.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import shapely

__all__ = ["tag_points"]


def tag_points(
    points: Iterable[Tuple[float, float]],
    polygons: Sequence["shapely.Polygon"],
) -> List[Optional[int]]:
    """Locate each point within a set of non-overlapping polygons.

    Parameters
    ----------
    points:
        ``(x, y)`` coordinate pairs.
    polygons:
        Shapely polygons in the same planar coordinate system as ``points``.
        Their interiors must not overlap, though they may share boundaries.

    Returns
    -------
    list
        One entry per input point, in input order: the index into ``polygons``
        of the polygon containing that point, or ``None`` if no polygon does.
        A point lying exactly on a boundary counts as contained; when that
        boundary is shared by several polygons, the smallest index is returned.

    Raises
    ------
    ValueError
        If ``points`` is not shaped like a sequence of ``(x, y)`` pairs.
    """
    coords = np.asarray(list(points), dtype="float64")
    n_points = len(coords)
    if n_points == 0:
        return []
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError("points must be a sequence of (x, y) coordinate pairs")

    polygons = list(polygons)
    n_polygons = len(polygons)
    if n_polygons == 0:
        return [None] * n_points

    # An STRtree turns this into one bbox query per point instead of a scan
    # over every polygon.  "intersects" is symmetric and, for a zero-dimensional
    # geometry, agrees with "covers", so points exactly on a boundary are
    # reported as hits -- which "contains" would not do.
    tree = shapely.STRtree(polygons)
    point_idx, polygon_idx = tree.query(shapely.points(coords), predicate="intersects")

    # A point on a shared boundary matches several polygons, so reduce each
    # point's hits to the lowest index.  n_polygons is not a valid index, so it
    # doubles as the "matched nothing" sentinel.
    best = np.full(n_points, n_polygons, dtype=np.int64)
    np.minimum.at(best, point_idx, polygon_idx)

    return [None if index == n_polygons else int(index) for index in best]
```