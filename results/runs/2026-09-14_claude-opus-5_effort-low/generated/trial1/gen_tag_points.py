"""Tag planar points with the index of the polygon that contains them.

A point lying exactly on a polygon boundary counts as contained; when several
polygons share that boundary, the smallest polygon index wins.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely.geometry import Polygon


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[Polygon],
) -> List[Optional[int]]:
    """Return, for each point, the index of the polygon covering it, else None.

    Parameters
    ----------
    points:
        Sequence of ``(x, y)`` tuples.
    polygons:
        Sequence of shapely ``Polygon`` objects in the same planar CRS as the
        points. Interiors are assumed not to overlap; shared boundaries are fine.

    Returns
    -------
    A list with one entry per input point, in input order.
    """
    n_points = len(points)
    result: List[Optional[int]] = [None] * n_points
    if n_points == 0 or len(polygons) == 0:
        return result

    coords = np.asarray(points, dtype="float64")
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError("points must be a sequence of (x, y) pairs")

    point_geoms = shapely.points(coords)

    # "covers" (unlike "contains") treats boundary points as inside.
    tree = shapely.STRtree(np.asarray(polygons, dtype=object))
    point_idx, poly_idx = tree.query(point_geoms, predicate="covers")
    if point_idx.size == 0:
        return result

    # Sort by (point, polygon) so the first hit per point is the smallest index.
    order = np.lexsort((poly_idx, point_idx))
    point_idx = point_idx[order]
    poly_idx = poly_idx[order]
    first = np.concatenate(([True], point_idx[1:] != point_idx[:-1]))

    for p, q in zip(point_idx[first].tolist(), poly_idx[first].tolist()):
        result[p] = q
    return result