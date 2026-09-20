"""Order-preserving deduplication of shapely geometries by topological equality."""

from __future__ import annotations

from typing import Iterable, List, Optional

import shapely
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]


def _bucket_key(geom: BaseGeometry) -> Optional[tuple]:
    """Cheap key that is identical for any two geometries covering the same point set.

    Bounds are derived directly from the coordinates (min/max), so geometries
    that describe the same set of points always share the exact same bounds
    regardless of vertex ordering, ring direction, or redundant vertices.
    All empty geometries share the key ``None`` (the empty set).
    """
    if geom.is_empty:
        return None
    return tuple(geom.bounds)


def dedupe_geoms(geoms: Iterable[BaseGeometry]) -> List[BaseGeometry]:
    """Return a new list with duplicate geometries removed, keeping first occurrences.

    Two geometries are considered duplicates when they describe exactly the same
    set of points in the plane (topological equality, ``shapely.equals``), even if
    their coordinate sequences differ, e.g. a ring written from a different start
    vertex, in the opposite direction, or with extra collinear vertices.
    """
    kept: List[BaseGeometry] = []
    # bucket key -> indices into `kept`; only same-bucket members need the
    # (comparatively expensive) exact topological equality check.
    buckets: dict = {}

    for geom in geoms:
        if geom is None:
            continue
        key = _bucket_key(geom)
        candidates = buckets.setdefault(key, [])
        duplicate = False
        for idx in candidates:
            if shapely.equals(kept[idx], geom):
                duplicate = True
                break
        if not duplicate:
            candidates.append(len(kept))
            kept.append(geom)

    return kept