"""Point-in-polygon tagging with boundary-inclusive, lowest-index tie-breaking."""

from typing import List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely.strtree import STRtree


def tag_points(
    points: Sequence[Tuple[float, float]], polygons: Sequence[Polygon]
) -> List[Optional[int]]:
    """Return, for each point, the index of the polygon containing it, or None.

    A point on a polygon's boundary counts as contained. If several polygons
    contain a point (shared boundary), the smallest index is returned.
    """
    n_points = len(points)
    if n_points == 0:
        return []
    if len(polygons) == 0:
        return [None] * n_points

    pts = shapely.points(np.asarray(points, dtype=float))
    tree = STRtree(list(polygons))

    # Bounding-box candidates, then exact boundary-inclusive test.
    pt_idx, poly_idx = tree.query(pts, predicate="intersects")

    result: List[Optional[int]] = [None] * n_points
    for i, j in zip(pt_idx.tolist(), poly_idx.tolist()):
        current = result[i]
        if current is None or j < current:
            result[i] = j
    return result