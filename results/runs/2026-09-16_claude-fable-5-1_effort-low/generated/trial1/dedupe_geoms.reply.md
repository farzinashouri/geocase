```python
"""Deduplicate shapely geometries by the set of points they describe.

Two geometries are treated as duplicates when they are topologically
equal (``shapely.equals``): they cover exactly the same set of points in
the plane, regardless of how their coordinate sequences are written
(different starting vertex, opposite ring orientation, redundant
collinear vertices, differing component order in multi-geometries, ...).

Candidates are bucketed by their exact bounding box before the
topological comparison, since geometries with the same point set
necessarily share a bounding box. This keeps the common case close to
linear while remaining exactly correct.
"""

from __future__ import annotations

import math
from typing import Hashable, Iterable, List, Optional, Tuple

import shapely
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]

_EMPTY_KEY: Tuple[str] = ("__empty__",)


def _bucket_key(geom: BaseGeometry) -> Hashable:
    """Return a hashable key shared by all geometries with the same point set."""
    if geom.is_empty:
        return _EMPTY_KEY
    bounds = tuple(float(v) for v in geom.bounds)
    if any(math.isnan(v) for v in bounds):
        return _EMPTY_KEY
    return bounds


def _same_points(a: BaseGeometry, b: BaseGeometry) -> bool:
    """True when ``a`` and ``b`` describe exactly the same set of points."""
    if a.is_empty and b.is_empty:
        return True
    if a.is_empty or b.is_empty:
        return False
    try:
        return bool(shapely.equals(a, b))
    except Exception:  # noqa: BLE001 - GEOS can raise on pathological input
        # Fall back to a coordinate-level comparison of canonical forms so
        # that at least literal / re-ordered duplicates are still caught.
        return bool(shapely.equals_exact(shapely.normalize(a), shapely.normalize(b)))


def dedupe_geoms(geoms: Iterable[Optional[BaseGeometry]]) -> List[Optional[BaseGeometry]]:
    """Remove duplicate geometries, keeping the first occurrence and the order.

    Parameters
    ----------
    geoms:
        An iterable of shapely geometries. ``None`` entries are kept once.

    Returns
    -------
    list
        A new list containing the first occurrence of each distinct
        geometry, in the original order. The input is not modified.
    """
    result: List[Optional[BaseGeometry]] = []
    buckets: dict = {}
    seen_none = False

    for geom in geoms:
        if geom is None:
            if not seen_none:
                seen_none = True
                result.append(None)
            continue

        key = _bucket_key(geom)
        bucket = buckets.setdefault(key, [])
        if any(_same_points(geom, kept) for kept in bucket):
            continue
        bucket.append(geom)
        result.append(geom)

    return result
```