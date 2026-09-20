"""Tag planar points with the index of the polygon that contains them.

`tag_points` assigns each input point to the polygon whose interior or
boundary contains it. Polygons are assumed non-overlapping in their
interiors, but may share boundaries; a point on a shared boundary is
assigned to the lowest-indexed polygon among those it touches.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely.strtree import STRtree


def tag_points(
    points: Iterable[Tuple[float, float]],
    polygons: Sequence[Polygon],
) -> List[Optional[int]]:
    """Return, for each point, the index of the containing polygon or None.

    Args:
        points: Iterable of ``(x, y)`` tuples.
        polygons: Sequence of shapely ``Polygon`` objects in the same
            coordinate system as ``points``. Interiors must not overlap;
            boundaries may be shared.

    Returns:
        A list with one entry per input point, in input order. Each entry
        is the index into ``polygons`` of the polygon containing the point
        (boundary inclusive), or ``None`` if no polygon contains it. When a
        point lies on a boundary shared by several polygons, the smallest
        such index is returned.
    """
    pts = list(points)
    polys = list(polygons)
    n_points = len(pts)
    n_polys = len(polys)

    result: List[Optional[int]] = [None] * n_points
    if n_points == 0 or n_polys == 0:
        return result

    coords = np.array([(float(x), float(y)) for x, y in pts], dtype=float)
    point_geoms = shapely.points(coords)

    tree = STRtree(polys)
    # ``intersects`` is boundary-inclusive: a point exactly on the polygon
    # edge (or on a vertex) counts as a hit.
    pt_idx, poly_idx = tree.query(point_geoms, predicate="intersects")

    if pt_idx.size == 0:
        return result

    # Keep the smallest polygon index for each point.
    best = np.full(n_points, n_polys, dtype=np.int64)
    np.minimum.at(best, pt_idx, poly_idx)

    for i in range(n_points):
        if best[i] < n_polys:
            result[i] = int(best[i])
    return result