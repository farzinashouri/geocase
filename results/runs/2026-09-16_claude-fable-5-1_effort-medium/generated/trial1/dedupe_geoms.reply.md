```python
"""Deduplicate shapely geometries by the set of points they cover.

Two geometries are considered duplicates when they are topologically equal
(``shapely.equals``), i.e. they describe exactly the same point set in the
plane regardless of vertex order, ring start vertex, ring orientation, or
redundant collinear vertices.  The first occurrence is kept and input order
is preserved.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Hashable, Iterable, List, Optional

import shapely
from shapely.geometry.base import BaseGeometry


def _bucket_key(geom: Optional[BaseGeometry]) -> Hashable:
    """Cheap invariant under topological equality, used to limit comparisons.

    Two topologically equal geometries have identical bounding boxes (bounds
    are exact min/max of coordinates of the same point set) and the same
    topological dimension.  Empty geometries all share one bucket.
    """
    if geom is None:
        return ("none",)
    if geom.is_empty:
        return ("empty",)
    # Dimension of the point set (0 = points, 1 = curves, 2 = areas).
    dim = shapely.get_dimensions(geom)
    return ("geom", int(dim), tuple(geom.bounds))


def _is_duplicate(geom: Optional[BaseGeometry], seen: List[Optional[BaseGeometry]]) -> bool:
    if geom is None:
        return any(s is None for s in seen)
    if geom.is_empty:
        # All empty geometries describe the same (empty) set of points.
        return True if seen else False
    for other in seen:
        if other is None:
            continue
        if geom.equals(other):
            return True
    return False


def dedupe_geoms(geoms: Iterable[Optional[BaseGeometry]]) -> List[Optional[BaseGeometry]]:
    """Return ``geoms`` with duplicates removed, keeping first occurrences in order.

    Duplicates are geometries that describe exactly the same set of points in
    the plane, e.g. a ring written from a different starting vertex or in the
    opposite direction, or a line with extra collinear vertices.
    """
    result: List[Optional[BaseGeometry]] = []
    buckets: defaultdict = defaultdict(list)

    for geom in geoms:
        key = _bucket_key(geom)
        bucket = buckets[key]
        if _is_duplicate(geom, bucket):
            continue
        bucket.append(geom)
        result.append(geom)

    return result


__all__ = ["dedupe_geoms"]
```