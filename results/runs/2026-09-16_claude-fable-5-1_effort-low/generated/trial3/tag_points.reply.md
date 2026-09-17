```python
"""Point-in-polygon tagging with boundary inclusion and lowest-index tie-breaking."""

from typing import List, Optional, Sequence, Tuple

import numpy as np
from shapely import STRtree, intersects, points as make_points
from shapely.geometry import Polygon


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[Polygon],
) -> List[Optional[int]]:
    """Return, for each point, the smallest index of a polygon containing it.

    Boundary points count as contained. Points in no polygon map to None.
    """
    n_points = len(points)
    if n_points == 0:
        return []
    if len(polygons) == 0:
        return [None] * n_points

    coords = np.asarray(points, dtype=float).reshape(n_points, 2)
    point_geoms = make_points(coords)

    result: List[Optional[int]] = [None] * n_points

    tree = STRtree(list(polygons))
    # Bounding-box candidates, then exact test. `intersects` on a point vs a
    # polygon is True for interior and boundary, which is the containment
    # semantics required here.
    point_idx, poly_idx = tree.query(point_geoms, predicate="intersects")

    if len(point_idx) == 0:
        return result

    # Sort by (point index, polygon index) so the first hit per point is the
    # smallest polygon index.
    order = np.lexsort((poly_idx, point_idx))
    point_idx = point_idx[order]
    poly_idx = poly_idx[order]

    first_positions = np.unique(point_idx, return_index=True)[1]
    for pos in first_positions:
        result[int(point_idx[pos])] = int(poly_idx[pos])

    return result
```