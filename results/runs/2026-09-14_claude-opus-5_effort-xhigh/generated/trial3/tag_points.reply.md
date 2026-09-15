```python
"""Tag planar points with the index of the polygon that contains them.

The polygons are assumed to have non-overlapping interiors, so a point can be
genuinely ambiguous only when it lies on a boundary shared by several polygons;
those cases resolve to the smallest polygon index.  Boundary points count as
contained, which is `covers` rather than `contains` in shapely terms.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely import Polygon

__all__ = ["tag_points"]


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[Polygon],
) -> List[Optional[int]]:
    """Return one polygon index (or None) per input point, in input order.

    Parameters
    ----------
    points:
        ``(x, y)`` tuples in the same planar coordinate system as ``polygons``.
    polygons:
        Shapely polygons with non-overlapping interiors.

    Returns
    -------
    list
        For each point, the index of the polygon covering it -- boundary
        included -- or ``None`` if no polygon covers it.  A point on a shared
        boundary gets the smallest index among the polygons covering it.
    """
    coords = _coordinate_array(points)
    polygons = list(polygons)
    n_points = len(coords)

    result: List[Optional[int]] = [None] * n_points
    if n_points == 0 or not polygons:
        return result

    point_geoms = shapely.points(coords)

    # Object arrays hold geometries without numpy trying to unpack them.
    polygon_geoms = np.empty(len(polygons), dtype=object)
    polygon_geoms[:] = polygons

    # Envelope prefilter, then an exact covers() test on the surviving pairs.
    point_idx, polygon_idx = shapely.STRtree(polygon_geoms).query(point_geoms)
    if point_idx.size == 0:
        return result

    # Preparing pays off whenever many points land in the same polygon.
    shapely.prepare(polygon_geoms[np.unique(polygon_idx)])
    covered = shapely.covers(polygon_geoms[polygon_idx], point_geoms[point_idx])
    point_idx = point_idx[covered]
    polygon_idx = polygon_idx[covered]

    # Sort by (point, polygon) so the first row for each point is its smallest
    # polygon index; query() does not promise either ordering.
    order = np.lexsort((polygon_idx, point_idx))
    point_idx = point_idx[order]
    polygon_idx = polygon_idx[order]
    is_first = np.ones(point_idx.shape, dtype=bool)
    is_first[1:] = point_idx[1:] != point_idx[:-1]

    for point, polygon in zip(point_idx[is_first], polygon_idx[is_first]):
        result[int(point)] = int(polygon)
    return result


def _coordinate_array(points: Sequence[Tuple[float, float]]) -> np.ndarray:
    """Normalize the input points to an ``(n, 2)`` float array."""
    coords = np.asarray(list(points), dtype=float)
    if coords.size == 0:
        return coords.reshape(0, 2)
    if coords.ndim != 2 or coords.shape[1] < 2:
        raise ValueError(
            f"points must be a sequence of (x, y) tuples, got array of shape "
            f"{coords.shape}"
        )
    return coords[:, :2]
```