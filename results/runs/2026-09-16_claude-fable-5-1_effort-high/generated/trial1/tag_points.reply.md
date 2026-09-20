Local test execution was blocked by the sandbox, so the module below is verified by inspection against shapely 2.1's `STRtree.query` semantics (array query returns `(input_idx, tree_idx)` pairs; the `intersects` predicate is boundary-inclusive).

```python
"""Assign each planar point to the index of the polygon that contains it.

Boundary points count as contained. When a point lies on a boundary shared by
several polygons, the smallest polygon index wins. Points outside every
polygon map to ``None``.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
from shapely import STRtree
from shapely import points as make_points
from shapely.geometry import Polygon


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[Polygon],
) -> List[Optional[int]]:
    """Return, per input point, the index of the polygon containing it.

    Args:
        points: Sequence of ``(x, y)`` tuples in the same planar CRS as
            ``polygons``.
        polygons: Sequence of shapely ``Polygon`` objects whose interiors do
            not overlap (shared boundaries are allowed).

    Returns:
        A list of the same length and order as ``points``. Each entry is the
        index into ``polygons`` of the polygon containing the point (boundary
        inclusive, smallest index on ties), or ``None`` if no polygon contains
        the point.
    """
    n = len(points)
    if n == 0 or len(polygons) == 0:
        return [None] * n

    coords = np.asarray(points, dtype=float).reshape(n, 2)
    point_geoms = make_points(coords)

    # Spatial index over the polygons; "intersects" is boundary-inclusive, so
    # a point exactly on an edge or vertex is reported as a hit.
    tree = STRtree(list(polygons))
    point_idx, poly_idx = tree.query(point_geoms, predicate="intersects")

    result: List[Optional[int]] = [None] * n
    for p, q in zip(point_idx.tolist(), poly_idx.tolist()):
        current = result[p]
        if current is None or q < current:
            result[p] = q
    return result
```