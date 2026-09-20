I couldn't run a sanity check (the Python invocation wasn't approved), so the module below is written to the shapely 2.x API without a local execution test.

```python
"""Tag planar points with the polygon that contains them.

The polygons are assumed to share boundaries but not to overlap in their
interiors, and to live in the same planar (projected) coordinate system as
the points. Boundary points count as contained; when a point falls on a
boundary shared by several polygons, the lowest polygon index wins.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely.strtree import STRtree

__all__ = ["tag_points"]


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[Polygon],
) -> List[Optional[int]]:
    """Return the containing polygon index for each point, or ``None``.

    Parameters
    ----------
    points:
        Sequence of ``(x, y)`` pairs.
    polygons:
        Sequence of shapely ``Polygon`` objects in the same planar CRS as
        ``points``. Interiors are assumed non-overlapping; shared boundaries
        are allowed.

    Returns
    -------
    list
        Exactly one entry per input point, in input order. Each entry is the
        index into ``polygons`` of the polygon covering that point (interior
        *or* boundary), or ``None`` if no polygon covers it. Points on a
        shared boundary resolve to the smallest matching index. Points with
        non-finite coordinates resolve to ``None``.

    Raises
    ------
    ValueError
        If ``points`` is not shaped like a sequence of ``(x, y)`` pairs.
    """
    polygons = list(polygons)
    coords = _as_xy(points)

    tags: List[Optional[int]] = [None] * len(coords)
    if not tags or not polygons:
        return tags

    # NaN/inf coordinates cannot be indexed meaningfully; leave them as None.
    usable = np.flatnonzero(np.isfinite(coords).all(axis=1))
    if usable.size == 0:
        return tags

    # `covers` is applied as tree_polygon.covers(point), which -- unlike
    # `contains` -- is true for points lying exactly on the boundary.
    tree = STRtree(polygons)
    point_pos, polygon_index = tree.query(
        shapely.points(coords[usable]), predicate="covers"
    )
    if point_pos.size == 0:
        return tags

    # A point may match several polygons along a shared boundary; keep the
    # smallest index. `minimum.at` is unbuffered, so duplicate positions
    # accumulate correctly.
    no_match = len(polygons)
    best = np.full(usable.size, no_match, dtype=np.int64)
    np.minimum.at(best, point_pos, polygon_index)

    for original_pos, polygon_pos in zip(usable.tolist(), best.tolist()):
        if polygon_pos != no_match:
            tags[original_pos] = polygon_pos
    return tags


def _as_xy(points: Sequence[Tuple[float, float]]) -> np.ndarray:
    """Coerce ``points`` to a float ``(N, 2)`` array."""
    coords = np.asarray(points, dtype="float64")
    if coords.size == 0:
        return coords.reshape(0, 2)
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError(
            "points must be a sequence of (x, y) pairs; "
            f"got an array of shape {coords.shape}"
        )
    return coords
```