"""Tag planar points with the index of the polygon that contains them.

The module is import-safe: it only imports third-party libraries and defines
one function.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely import STRtree
from shapely.geometry import Polygon

__all__ = ["tag_points"]

# Sentinel used while reducing candidate polygon indices to their minimum.
_NO_HIT = np.iinfo(np.int64).max


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[Polygon],
) -> List[Optional[int]]:
    """Return, for each point, the index of the polygon covering it.

    Parameters
    ----------
    points:
        Sequence of ``(x, y)`` tuples in the same planar CRS as ``polygons``.
    polygons:
        Sequence of shapely ``Polygon`` objects with non-overlapping interiors
        (shared boundaries are allowed).

    Returns
    -------
    list
        One entry per input point, in input order: the index into ``polygons``
        of the polygon covering the point, or ``None`` if no polygon does. A
        point exactly on a boundary counts as covered; if several polygons
        share that boundary, the smallest of their indices is returned.
    """
    n_points = len(points)
    result: List[Optional[int]] = [None] * n_points
    if n_points == 0 or len(polygons) == 0:
        return result

    coords = np.asarray(points, dtype="float64").reshape(n_points, 2)
    point_geoms = shapely.points(coords)

    tree = STRtree(polygons)
    # The predicate is evaluated as predicate(input_geometry, tree_geometry),
    # so "covered_by" asks whether each point lies in the polygon's interior
    # *or* on its boundary -- exactly the containment rule we want.
    point_idx, polygon_idx = tree.query(point_geoms, predicate="covered_by")
    if point_idx.size == 0:
        return result

    # A point on a shared edge matches several polygons; keep the lowest index.
    best = np.full(n_points, _NO_HIT, dtype=np.int64)
    np.minimum.at(best, point_idx, polygon_idx.astype(np.int64))

    for i in np.nonzero(best != _NO_HIT)[0]:
        result[int(i)] = int(best[i])
    return result