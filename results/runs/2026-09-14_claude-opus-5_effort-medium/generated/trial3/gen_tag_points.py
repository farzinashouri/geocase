"""Point-in-polygon tagging.

Assigns each input point the index of the polygon that contains it, treating
points that lie exactly on a polygon boundary as contained.  Importing this
module has no side effects.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely.geometry.base import BaseGeometry

__all__ = ["tag_points"]


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[BaseGeometry],
) -> List[Optional[int]]:
    """Tag each point with the index of the polygon covering it.

    Parameters
    ----------
    points:
        Sequence of ``(x, y)`` coordinate pairs.
    polygons:
        Sequence of shapely ``Polygon`` (or ``MultiPolygon``) geometries in the
        same planar coordinate system as ``points``.  Interiors are assumed not
        to overlap, but boundaries may be shared.

    Returns
    -------
    list
        One entry per input point, in input order: the index of the covering
        polygon, or ``None`` if the point lies in no polygon.  A point on a
        boundary shared by several polygons gets the smallest such index.
    """
    coords = _as_coords(points)
    n_points = len(coords)

    if n_points == 0:
        return []

    result: List[Optional[int]] = [None] * n_points

    if len(polygons) == 0:
        return result

    # shapely.points() propagates NaN into the geometry, but a NaN point cannot
    # be covered by anything, so such rows simply stay None.
    point_geoms = shapely.points(coords)

    tree = shapely.STRtree(np.asarray(polygons, dtype=object))

    # `covers` is evaluated as tree_geometry.covers(query_geometry), which is
    # exactly the "boundary counts as inside" containment test we want.
    # Returns a (2, M) array of (point index, polygon index) pairs.
    pairs = tree.query(point_geoms, predicate="covers")

    if pairs.size == 0:
        return result

    point_idx, poly_idx = pairs

    # Sort by point index, then polygon index, so the first hit for each point
    # is the smallest covering polygon index.
    order = np.lexsort((poly_idx, point_idx))
    point_idx = point_idx[order]
    poly_idx = poly_idx[order]

    first = np.empty(point_idx.shape, dtype=bool)
    first[0] = True
    np.not_equal(point_idx[1:], point_idx[:-1], out=first[1:])

    for p_i, g_i in zip(point_idx[first].tolist(), poly_idx[first].tolist()):
        result[p_i] = g_i

    return result


def _as_coords(points: Iterable[Tuple[float, float]]) -> np.ndarray:
    """Coerce the input points to an (N, 2) float array."""
    coords = np.asarray(list(points), dtype=float)

    if coords.size == 0:
        return coords.reshape(0, 2)

    if coords.ndim != 2 or coords.shape[1] < 2:
        raise ValueError("points must be a sequence of (x, y) coordinate pairs")

    return coords[:, :2]