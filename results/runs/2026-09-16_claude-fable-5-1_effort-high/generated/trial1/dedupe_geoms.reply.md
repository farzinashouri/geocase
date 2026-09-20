Here is the module.

```python
"""Remove duplicate shapely geometries while preserving first-seen order.

Two geometries count as duplicates when they describe exactly the same set of
points in the plane, regardless of how their coordinate sequences are written
(ring start vertex, ring orientation, redundant collinear vertices, single-part
multi-geometry vs. its part, ...).  Z/M values are ignored, matching the
"in the plane" definition.
"""

from __future__ import annotations

from typing import Dict, Hashable, Iterable, List, Optional

import shapely
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]

_EMPTY_KEY: Hashable = ("<empty>",)
_NONE_KEY: Hashable = ("<none>",)


def _bucket_key(geom: Optional[BaseGeometry]) -> Hashable:
    """Cheap key such that point-set-equal geometries always share a bucket.

    The bounding box is a function of the point set alone, so geometries that
    describe the same set of points necessarily have identical bounds.
    """
    if geom is None:
        return _NONE_KEY
    if geom.is_empty:
        return _EMPTY_KEY
    return tuple(geom.bounds)


def _same_point_set(a: BaseGeometry, b: BaseGeometry) -> bool:
    """True when ``a`` and ``b`` describe the same set of points in the plane."""
    # Topological equality is exactly the "same point set" relation and is
    # insensitive to coordinate ordering, orientation and redundant vertices.
    try:
        return bool(shapely.equals(a, b))
    except Exception:  # noqa: BLE001 - GEOS may throw on invalid geometries
        pass
    # Fallback for geometries GEOS refuses to relate: compare canonical forms.
    try:
        return bool(shapely.equals_exact(shapely.normalize(a), shapely.normalize(b), 0.0))
    except Exception:  # noqa: BLE001
        return a.wkb == b.wkb


def dedupe_geoms(geoms: Iterable[Optional[BaseGeometry]]) -> List[Optional[BaseGeometry]]:
    """Return ``geoms`` with duplicates removed, keeping the first occurrence.

    Order of the surviving geometries is the order of their first appearance.
    Every empty geometry (of any type) is treated as the same empty point set;
    ``None`` entries are kept once, at the position of the first ``None``.
    """
    kept: List[Optional[BaseGeometry]] = []
    buckets: Dict[Hashable, List[BaseGeometry]] = {}
    seen_none = False

    for geom in geoms:
        if geom is None:
            if not seen_none:
                seen_none = True
                kept.append(None)
            continue
        if not isinstance(geom, BaseGeometry):
            raise TypeError(f"expected a shapely geometry, got {type(geom).__name__}")

        key = _bucket_key(geom)
        bucket = buckets.setdefault(key, [])

        if key is _EMPTY_KEY:
            if not bucket:
                bucket.append(geom)
                kept.append(geom)
            continue

        if any(_same_point_set(geom, other) for other in bucket):
            continue

        bucket.append(geom)
        kept.append(geom)

    return kept
```