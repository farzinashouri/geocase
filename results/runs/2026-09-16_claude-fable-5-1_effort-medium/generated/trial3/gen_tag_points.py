"""Point-in-polygon tagging.

Provides ``tag_points`` which assigns each planar point to the index of
the polygon that contains it (boundary inclusive), or ``None`` if no
polygon contains it. When a point lies on a boundary shared by several
polygons, the smallest polygon index wins.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
from shapely import STRtree, points as make_points
from shapely.geometry import Polygon


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[Polygon],
) -> List[Optional[int]]:
    """Return, per input point, the index of the polygon containing it.

    A point on a polygon's boundary counts as contained. If several
    polygons contain the point (only possible on shared boundaries,
    since interiors do not overlap), the smallest index is returned.
    Points contained in no polygon map to ``None``. Output order
    matches input order and has exactly one entry per input point.
    """
    n_points = len(points)
    result: List[Optional[int]] = [None] * n_points
    if n_points == 0 or len(polygons) == 0:
        return result

    coords = np.asarray(points, dtype=float).reshape(n_points, 2)
    point_geoms = make_points(coords)

    tree = STRtree(list(polygons))
    # ``intersects`` for a point against a polygon is true for the
    # interior and the boundary, which is exactly "contained" here.
    point_idx, poly_idx = tree.query(point_geoms, predicate="intersects")

    for p_i, g_i in zip(point_idx.tolist(), poly_idx.tolist()):
        current = result[p_i]
        if current is None or g_i < current:
            result[p_i] = g_i

    return result