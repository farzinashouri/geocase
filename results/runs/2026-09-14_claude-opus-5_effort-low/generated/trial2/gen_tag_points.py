"""Assign each point to the polygon that contains it.

Boundary points count as contained; when a point lies on a boundary shared by
several polygons, the smallest polygon index wins.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
from shapely import STRtree
from shapely.geometry import Point, Polygon


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[Polygon],
) -> List[Optional[int]]:
    """Return, for each point, the index of the polygon covering it, else None.

    Parameters
    ----------
    points:
        Sequence of ``(x, y)`` coordinate pairs.
    polygons:
        Sequence of shapely ``Polygon`` objects in the same planar CRS as the
        points. Interiors are assumed non-overlapping, but boundaries may be
        shared.

    Returns
    -------
    list
        One entry per input point, in input order: the smallest index of a
        polygon that covers the point (boundary included), or ``None``.
    """
    points = list(points)
    result: List[Optional[int]] = [None] * len(points)
    if not points or len(polygons) == 0:
        return result

    point_geoms = [Point(x, y) for x, y in points]
    tree = STRtree(list(polygons))

    # "covers" treats boundary-touching points as contained, which is exactly
    # the containment rule we want. Tree indices match input order.
    point_idx, poly_idx = tree.query(point_geoms, predicate="covers")
    if point_idx.size == 0:
        return result

    # np.minimum.at gives the smallest polygon index per point in one pass.
    best = np.full(len(points), np.iinfo(np.int64).max, dtype=np.int64)
    np.minimum.at(best, point_idx, poly_idx.astype(np.int64))

    for i in np.unique(point_idx):
        result[int(i)] = int(best[i])
    return result


def _as_point_list(points: Iterable[Tuple[float, float]]) -> List[Tuple[float, float]]:
    return [(float(x), float(y)) for x, y in points]