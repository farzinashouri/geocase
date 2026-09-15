```python
"""Order-preserving deduplication of shapely geometries by point-set equality.

Two geometries are treated as duplicates when they cover exactly the same set of
points in the plane, regardless of how their coordinate sequences are written
(different start vertex, reversed ring orientation, redundant nodes, ...).
"""

from __future__ import annotations

from typing import Hashable, Iterable, List, Optional

import shapely
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]

# Bounds are bucketed before the (relatively expensive) topological comparison.
# The rounding is deliberately coarse so that geometries which are equal but
# differ by floating-point noise still land in the same bucket; exactness is
# still decided by shapely.equals, never by the bucket key.
_BOUNDS_DECIMALS = 9


def _exact_key(geom: BaseGeometry) -> Optional[Hashable]:
    """Return a hashable key that is identical for normalized-identical geoms.

    ``shapely.normalize`` rewrites a geometry into a canonical form (ring start
    vertex, orientation and component order), so geometries that differ only in
    how their coordinates were written share a WKB. Returns ``None`` when no
    such key can be built, in which case the caller falls back to comparison.
    """
    try:
        return shapely.to_wkb(shapely.normalize(geom), include_srid=False)
    except Exception:
        return None


def _bucket_key(geom: BaseGeometry) -> Hashable:
    """Cheap key grouping geometries that could possibly be equal."""
    if geom.is_empty:
        return ("empty",)
    minx, miny, maxx, maxy = geom.bounds
    return (
        round(minx, _BOUNDS_DECIMALS),
        round(miny, _BOUNDS_DECIMALS),
        round(maxx, _BOUNDS_DECIMALS),
        round(maxy, _BOUNDS_DECIMALS),
    )


def _same_point_set(a: BaseGeometry, b: BaseGeometry) -> bool:
    if a.is_empty or b.is_empty:
        return a.is_empty and b.is_empty
    try:
        return bool(shapely.equals(a, b))
    except shapely.errors.GEOSException:
        # Invalid input (self-intersecting ring, etc.) can make the topological
        # predicate fail; fall back to a structural comparison.
        return bool(shapely.equals_exact(shapely.normalize(a), shapely.normalize(b)))


def dedupe_geoms(geoms: Iterable[BaseGeometry]) -> List[BaseGeometry]:
    """Return the geometries with duplicates removed, first occurrence kept.

    Order is preserved. ``None`` entries are collapsed to a single ``None``,
    mirroring the treatment of duplicate geometries.

    Raises:
        TypeError: if an element is neither ``None`` nor a shapely geometry.
    """
    kept: List[BaseGeometry] = []
    seen_exact: set = set()
    seen_none = False
    # bucket key -> indices into `kept`, so comparison stays local.
    buckets: dict = {}

    for geom in geoms:
        if geom is None:
            if seen_none:
                continue
            seen_none = True
            kept.append(None)
            continue

        if not isinstance(geom, BaseGeometry):
            raise TypeError(f"expected a shapely geometry or None, got {type(geom)!r}")

        key = _exact_key(geom)
        if key is not None and key in seen_exact:
            continue

        bucket = buckets.setdefault(_bucket_key(geom), [])
        if any(_same_point_set(geom, kept[i]) for i in bucket):
            continue

        bucket.append(len(kept))
        kept.append(geom)
        if key is not None:
            seen_exact.add(key)

    return kept
```