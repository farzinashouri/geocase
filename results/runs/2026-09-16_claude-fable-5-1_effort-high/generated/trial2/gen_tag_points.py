"""Assign planar points to the polygons that contain them.

The single public function, ``tag_points``, maps each ``(x, y)`` point to the
index of the shapely ``Polygon`` that contains it. Boundary points count as
contained, and a point on a boundary shared by several polygons is assigned
to the polygon with the smallest index. Points outside every polygon map to
``None``.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely.strtree import STRtree

__all__ = ["tag_points"]


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[Polygon],
) -> List[Optional[int]]:
    """Return, per input point, the index of the containing polygon or ``None``.

    Parameters
    ----------
    points:
        Iterable of ``(x, y)`` pairs in the same planar coordinate system as
        ``polygons``.
    polygons:
        Sequence of shapely ``Polygon`` objects whose interiors do not overlap
        (shared boundaries are allowed).

    Returns
    -------
    list
        One entry per point, in input order. Each entry is the smallest index
        of a polygon that contains the point (boundary inclusive), or ``None``
        when no polygon contains it.
    """
    point_list = list(points)
    polygon_list = list(polygons)
    n_points = len(point_list)
    n_polys = len(polygon_list)

    result: List[Optional[int]] = [None] * n_points
    if n_points == 0 or n_polys == 0:
        return result

    coords = np.array(
        [(float(x), float(y)) for x, y in point_list], dtype=float
    ).reshape(n_points, 2)
    point_geoms = shapely.points(coords)

    try:
        in_idx, tree_idx = _query_tree(point_geoms, polygon_list)
    except shapely.errors.GEOSException:
        # Some polygon is topologically invalid; repair copies and retry.
        repaired = [
            shapely.make_valid(p) if p is not None and not p.is_empty else p
            for p in polygon_list
        ]
        in_idx, tree_idx = _query_tree(point_geoms, repaired)

    if in_idx.size == 0:
        return result

    # For every point keep the smallest polygon index that hit it. Using a
    # sentinel of ``n_polys`` lets ``np.minimum.at`` accumulate directly.
    best = np.full(n_points, n_polys, dtype=np.int64)
    np.minimum.at(best, in_idx, tree_idx)

    for i, b in enumerate(best.tolist()):
        if b < n_polys:
            result[i] = int(b)
    return result


def _query_tree(point_geoms, polygon_list):
    """Return (point_index, polygon_index) arrays for every intersecting pair.

    ``intersects`` is boundary-inclusive, so points on an edge or vertex of a
    polygon are reported as hits. The spatial index makes this scale well for
    large inputs while remaining exact.
    """
    tree = STRtree(polygon_list)
    pairs = tree.query(point_geoms, predicate="intersects")
    pairs = np.asarray(pairs, dtype=np.int64).reshape(2, -1)
    return pairs[0], pairs[1]