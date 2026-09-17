Sandbox denied file writes and Python execution, so the module below is unverified by a run, but the logic relies only on shapely 2's documented `STRtree.query` bulk semantics.

```python
"""Assign planar points to the polygons that contain them.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[BaseGeometry],
) -> List[Optional[int]]:
    """Return, for each point, the index of the polygon that contains it.

    A point lying exactly on a polygon's boundary counts as contained. If a
    point lies on a boundary shared by several polygons, the smallest polygon
    index is returned. Points that fall in no polygon map to ``None``.

    Parameters
    ----------
    points:
        Sequence of ``(x, y)`` tuples in the same planar coordinate system as
        ``polygons``.
    polygons:
        Sequence of shapely ``Polygon`` geometries whose interiors do not
        overlap. Empty or ``None`` entries are ignored (never matched).

    Returns
    -------
    list
        One entry per input point, in input order: an ``int`` polygon index or
        ``None``.
    """
    n_points = len(points)
    if n_points == 0:
        return []

    # Drop empty/missing polygons but remember their original positions so the
    # returned indices refer to the caller's list.
    kept: List[BaseGeometry] = []
    original_index: List[int] = []
    for i, poly in enumerate(polygons):
        if poly is None or poly.is_empty:
            continue
        kept.append(poly)
        original_index.append(i)

    result: List[Optional[int]] = [None] * n_points
    if not kept:
        return result

    coords = np.array(
        [(float(p[0]), float(p[1])) for p in points], dtype=float
    ).reshape(-1, 2)
    query_points = shapely.points(coords)

    tree = STRtree(kept)
    # Bulk query returns a (2, k) array: row 0 holds indices into
    # ``query_points``, row 1 holds indices into ``kept``. For a point and a
    # polygon, "intersects" is true when the point is in the interior *or* on
    # the boundary, which is exactly the containment rule required here.
    point_idx, tree_idx = tree.query(query_points, predicate="intersects")
    if point_idx.size == 0:
        return result

    mapped = np.asarray(original_index, dtype=np.int64)[tree_idx]

    # Sort hits by (point index, original polygon index) so that the first hit
    # for each point is the smallest polygon index.
    order = np.lexsort((mapped, point_idx))
    point_idx = point_idx[order]
    mapped = mapped[order]

    first_hit = np.ones(point_idx.shape, dtype=bool)
    first_hit[1:] = point_idx[1:] != point_idx[:-1]

    for p, m in zip(point_idx[first_hit], mapped[first_hit]):
        result[int(p)] = int(m)

    return result


__all__ = ["tag_points"]
```