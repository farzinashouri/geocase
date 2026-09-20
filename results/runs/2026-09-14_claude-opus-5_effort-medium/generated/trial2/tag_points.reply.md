```python
"""Tag planar points with the index of the polygon that contains them.

Boundary-inclusive: a point lying exactly on a polygon's boundary counts as
contained.  Where a point falls on a boundary shared by several polygons, the
smallest polygon index wins.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely.geometry import Polygon

__all__ = ["tag_points"]


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[Polygon],
) -> List[Optional[int]]:
    """Return, for each point, the index of the polygon covering it, else None.

    Parameters
    ----------
    points:
        Sequence of ``(x, y)`` tuples in the same planar CRS as ``polygons``.
    polygons:
        Sequence of shapely ``Polygon`` (or ``MultiPolygon``) geometries with
        non-overlapping interiors; shared boundaries are allowed.

    Returns
    -------
    list
        One entry per input point, in input order.  Each entry is the smallest
        index ``i`` such that ``polygons[i]`` covers the point (interior or
        boundary), or ``None`` when no polygon covers it.
    """
    pts = list(points) if not isinstance(points, list) else points
    n_points = len(pts)
    if n_points == 0:
        return []

    result: List[Optional[int]] = [None] * n_points

    polys = list(polygons)
    if not polys:
        return result

    coords = np.asarray(pts, dtype="float64").reshape(n_points, 2)
    point_geoms = shapely.points(coords)

    # `covers` is the boundary-inclusive counterpart of `contains`: the tree
    # geometry (a polygon) covers the query geometry (a point).
    tree = shapely.STRtree(np.asarray(polys, dtype=object))
    poly_idx, point_idx = tree.query(point_geoms, predicate="covers", indices=True)

    if poly_idx.size == 0:
        return result

    # `query` pairs are (index into point_geoms, index into the tree geoms).
    # Reduce to the smallest polygon index per point, which resolves points
    # sitting on a boundary shared by several polygons.
    winners = np.full(n_points, np.iinfo(np.int64).max, dtype="int64")
    np.minimum.at(winners, poly_idx, point_idx.astype("int64"))

    hit = np.flatnonzero(winners != np.iinfo(np.int64).max)
    for i in hit:
        result[int(i)] = int(winners[i])
    return result


def _self_check() -> None:  # pragma: no cover - manual sanity helper
    a = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    b = Polygon([(1, 0), (2, 0), (2, 1), (1, 1)])
    assert tag_points(
        [(0.5, 0.5), (1.5, 0.5), (1.0, 0.5), (5.0, 5.0)], [a, b]
    ) == [0, 1, 0, None]
```