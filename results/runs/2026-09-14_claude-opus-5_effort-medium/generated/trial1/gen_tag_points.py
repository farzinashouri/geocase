"""Point-in-polygon tagging for planar (x, y) data.

``tag_points(points, polygons)`` returns, for every input point, the index of
the polygon that contains it -- boundaries included -- or ``None`` when the
point falls outside every polygon.  Polygon interiors are assumed disjoint, so
the only way a point can match more than one polygon is by lying on a shared
boundary; in that case the smallest matching index wins.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely import STRtree

__all__ = ["tag_points"]


def tag_points(
    points: Iterable[Tuple[float, float]],
    polygons: Sequence["shapely.Polygon"],
) -> List[Optional[int]]:
    """Tag each point with the index of the polygon covering it.

    Parameters
    ----------
    points:
        Iterable of ``(x, y)`` tuples in the same planar CRS as ``polygons``.
    polygons:
        Sequence of shapely ``Polygon`` (or ``MultiPolygon``) geometries with
        non-overlapping interiors.

    Returns
    -------
    list
        One entry per input point, in input order: the smallest index ``i``
        such that ``polygons[i]`` covers the point (boundary counts as
        covered), else ``None``.
    """
    coords = np.asarray(list(points), dtype="float64")
    if coords.size == 0:
        return []
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError("points must be a sequence of (x, y) pairs")

    n_points = coords.shape[0]
    result: List[Optional[int]] = [None] * n_points

    polygons = list(polygons)
    if not polygons:
        return result

    # `covers` (rather than `contains`) is what makes boundary points count as
    # inside; the STRtree prefilters by bounding box so we only run the exact
    # predicate on plausible candidates.
    geoms = shapely.points(coords[:, 0], coords[:, 1])
    tree = STRtree(polygons)
    point_idx, poly_idx = tree.query(geoms, predicate="covers")

    if point_idx.size == 0:
        return result

    # A point can match several polygons only along a shared boundary; keep the
    # lowest index.  Query results come back in no guaranteed order, so reduce
    # with a minimum rather than relying on a first/last hit.
    sentinel = len(polygons)
    best = np.full(n_points, sentinel, dtype="int64")
    np.minimum.at(best, point_idx, poly_idx)

    for i in np.flatnonzero(best < sentinel):
        result[int(i)] = int(best[i])
    return result