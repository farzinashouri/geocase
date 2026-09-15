```python
"""Tag planar points with the index of the polygon that contains them.

The polygons are assumed to share boundaries but not interiors, so a point can
match more than one polygon only by lying on a shared boundary.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely.geometry import Polygon


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[Polygon],
) -> list[Optional[int]]:
    """Return, for each point, the index of the polygon containing it.

    Parameters
    ----------
    points:
        Sequence of ``(x, y)`` pairs.
    polygons:
        Sequence of shapely ``Polygon`` objects in the same planar coordinate
        system as ``points``. Interiors are assumed not to overlap.

    Returns
    -------
    list
        One entry per input point, in input order: the index into ``polygons``
        of the containing polygon, or ``None`` if the point is in no polygon.
        A point exactly on a boundary counts as contained; if that boundary is
        shared by several polygons, the smallest index is returned.
    """
    coords = np.asarray(points, dtype=np.float64)
    if coords.size == 0:
        return []
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError("points must be a sequence of (x, y) pairs")

    result: list[Optional[int]] = [None] * coords.shape[0]

    polygons = list(polygons)
    if not polygons:
        return result

    point_geoms = shapely.points(coords)

    # Caching prepared versions of the polygons makes the per-point predicate
    # evaluations cheap; it only populates an internal cache on the geometries.
    shapely.prepare(polygons)
    tree = shapely.STRtree(polygons)

    # The predicate is evaluated as predicate(input_geometry, tree_geometry).
    # `intersects` is symmetric and, for a point against a closed polygon, is
    # true exactly when the point is in the interior or on the boundary, which
    # is the containment rule we want.
    point_idx, poly_idx = tree.query(point_geoms, predicate="intersects")
    if point_idx.size == 0:
        return result

    # Sort hits by point, then by polygon index, and keep the first hit of each
    # point so that the smallest polygon index wins on shared boundaries.
    order = np.lexsort((poly_idx, point_idx))
    point_idx = point_idx[order]
    poly_idx = poly_idx[order]

    first = np.empty(point_idx.shape, dtype=bool)
    first[0] = True
    np.not_equal(point_idx[1:], point_idx[:-1], out=first[1:])

    for point_pos, polygon_pos in zip(
        point_idx[first].tolist(), poly_idx[first].tolist()
    ):
        result[point_pos] = polygon_pos

    return result
```