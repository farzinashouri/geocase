Writing a shapely STRtree-based implementation.

```python
"""Tag planar points with the index of the polygon that contains them."""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely.strtree import STRtree


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[Polygon],
) -> list[Optional[int]]:
    """Return, for each point, the index of the polygon containing it.

    A point on a polygon's boundary counts as contained. If a point lies on a
    boundary shared by several polygons, the smallest polygon index is
    returned. Points inside no polygon map to ``None``. The output has exactly
    one entry per input point, in input order.
    """
    points = list(points)
    polygons = list(polygons)
    n_points = len(points)
    result: list[Optional[int]] = [None] * n_points

    if n_points == 0 or len(polygons) == 0:
        return result

    coords = np.asarray(points, dtype=float).reshape(n_points, 2)
    point_geoms = shapely.points(coords)

    tree = STRtree(polygons)
    # For a point and a polygon, "intersects" is true exactly when the point is
    # in the interior or on the boundary, which is the containment rule wanted.
    point_idx, poly_idx = tree.query(point_geoms, predicate="intersects")

    for p, g in zip(point_idx.tolist(), poly_idx.tolist()):
        current = result[p]
        if current is None or g < current:
            result[p] = g

    return result
```