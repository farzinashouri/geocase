```python
"""Tag planar points with the index of the polygon that contains them.

A point on a polygon boundary counts as contained; ties (shared boundaries)
resolve to the smallest polygon index.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
from shapely import STRtree
from shapely.geometry import Point, Polygon

__all__ = ["tag_points"]


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[Polygon],
) -> List[Optional[int]]:
    """Return, for each point, the index of the polygon covering it, else None.

    ``points`` and ``polygons`` must share a planar coordinate system. Polygon
    interiors are assumed non-overlapping, but boundaries may be shared; a point
    on a shared boundary is assigned the smallest matching index.
    """
    points = list(points)
    polygons = list(polygons)

    if not points:
        return []
    if not polygons:
        return [None] * len(points)

    geoms = [Point(x, y) for x, y in points]
    tree = STRtree(polygons)

    # Bounding-box prefilter, then exact "covers" test (boundary inclusive).
    candidate_points, candidate_polys = tree.query(geoms, predicate="covers")

    out: List[Optional[int]] = [None] * len(points)
    if len(candidate_points):
        # Descending order so the smallest polygon index is written last.
        order = np.lexsort((-candidate_polys, candidate_points))
        for pos in order:
            out[int(candidate_points[pos])] = int(candidate_polys[pos])
    return out
```