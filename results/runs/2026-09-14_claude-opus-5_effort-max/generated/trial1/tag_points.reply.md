I couldn't run Python here to smoke-test (commands need approval), so this is written against the documented shapely 2.x `STRtree.query` semantics — the predicate is evaluated as `predicate(input_geometry, tree_geometry)`, so putting the *points* in the tree and querying with *polygons* under `"covers"` gives `polygon.covers(point)` (boundary counts as contained) and lets shapely prepare each polygon.

```python
"""Tag planar points with the index of the polygon that contains them.

The module is pure library code: importing it has no side effects.
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
    """Map each point to the index of the polygon covering it.

    Parameters
    ----------
    points:
        Iterable of ``(x, y)`` pairs.
    polygons:
        Sequence of shapely polygons in the same planar coordinate system as
        ``points``. Interiors are assumed not to overlap, though boundaries may
        be shared.

    Returns
    -------
    list
        One entry per input point, in input order: the index into ``polygons``
        of the polygon covering that point, or ``None`` if no polygon does. A
        point exactly on a boundary counts as contained; when that boundary is
        shared by several polygons, the smallest index is returned.

    Notes
    -----
    Points are indexed in an STRtree and each polygon is queried against it, so
    the polygons -- not the points -- are the prepared side of the predicate.
    That is the cheaper direction when polygons have many vertices.
    """
    coords = _as_coords(points)
    polys = np.asarray(list(polygons), dtype=object)

    tags: List[Optional[int]] = [None] * len(coords)
    if len(coords) == 0 or len(polys) == 0:
        return tags

    tree = STRtree(shapely.points(coords))

    # STRtree evaluates ``predicate(input_geometry, tree_geometry)``, i.e.
    # ``polygon.covers(point)``. ``covers`` -- unlike ``contains`` -- is true
    # for points lying exactly on the boundary. Empty or None polygons simply
    # never match.
    poly_idx, point_idx = tree.query(polys, predicate="covers")

    # Ties (shared boundaries) resolve to the smallest polygon index: sort the
    # hits by point, then by polygon index, and keep the first hit per point.
    order = np.lexsort((poly_idx, point_idx))
    poly_idx = poly_idx[order]
    point_idx = point_idx[order]
    first = np.empty(point_idx.shape, dtype=bool)
    first[:1] = True
    first[1:] = point_idx[1:] != point_idx[:-1]

    for point, polygon in zip(point_idx[first].tolist(), poly_idx[first].tolist()):
        tags[point] = polygon
    return tags


def _as_coords(points: Iterable[Tuple[float, float]]) -> np.ndarray:
    """Coerce ``points`` to an ``(N, 2)`` float array."""
    coords = np.asarray(list(points), dtype=np.float64)
    if coords.size == 0:
        return coords.reshape(0, 2)
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError(
            "points must be a sequence of (x, y) pairs, got an array of shape "
            f"{coords.shape}"
        )
    return coords
```