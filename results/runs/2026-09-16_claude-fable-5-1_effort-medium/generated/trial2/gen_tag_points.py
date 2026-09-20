"""Tag planar points with the index of the polygon that contains them."""

from typing import List, Optional, Sequence, Tuple

import numpy as np
from shapely import Polygon, STRtree, points as make_points


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[Polygon],
) -> List[Optional[int]]:
    """Return, for each point, the index of the containing polygon or None.

    A point on a polygon's boundary counts as contained. If a point lies on a
    boundary shared by several polygons, the smallest polygon index is returned.
    """
    n_points = len(points)
    result: List[Optional[int]] = [None] * n_points
    if n_points == 0 or len(polygons) == 0:
        return result

    coords = np.asarray(points, dtype=float).reshape(n_points, 2)
    point_geoms = make_points(coords)

    tree = STRtree(list(polygons))
    # "intersects" is closed: it includes points exactly on the boundary.
    point_idx, poly_idx = tree.query(point_geoms, predicate="intersects")

    for p, g in zip(point_idx.tolist(), poly_idx.tolist()):
        current = result[p]
        if current is None or g < current:
            result[p] = g

    return result