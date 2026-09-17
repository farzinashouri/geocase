"""Deduplicate shapely geometries by the set of points they describe.

Two geometries count as duplicates when they are topologically equal, i.e.
they cover exactly the same point set in the plane. This is independent of
how the coordinate sequence is written: a ring started from a different
vertex, a reversed ring or line, or a line with an extra collinear vertex
all compare as equal to their simpler counterparts.
"""

from __future__ import annotations

from typing import Any, Dict, Hashable, Iterable, List

import shapely
from shapely.errors import GEOSException


def _bucket_key(geom: Any) -> Hashable:
    """Cheap key that is invariant under coordinate re-ordering.

    Geometries describing the same point set always share a bounding box, so
    the bounds can be used to narrow down which candidates need the expensive
    topological comparison. Empty geometries all describe the empty set and
    therefore share a single bucket.
    """
    if geom is None:
        return ("none",)
    if geom.is_empty:
        return ("empty",)
    return ("geom", tuple(geom.bounds))


def _same_point_set(a: Any, b: Any) -> bool:
    """True when *a* and *b* cover exactly the same points in the plane."""
    if a is None or b is None:
        return a is None and b is None
    if a.is_empty or b.is_empty:
        return a.is_empty and b.is_empty
    try:
        return bool(shapely.equals(a, b))
    except GEOSException:
        # Topological comparison can fail on invalid geometries; fall back to
        # comparing canonical coordinate representations.
        try:
            return shapely.normalize(a).wkb == shapely.normalize(b).wkb
        except GEOSException:
            return a.wkb == b.wkb


def dedupe_geoms(geoms: Iterable[Any]) -> List[Any]:
    """Return a new list with duplicate geometries removed.

    The first occurrence of each distinct point set is kept and the original
    order is preserved. Geometries are compared topologically, so differing
    coordinate sequences that describe the same shape are treated as equal.
    """
    kept: List[Any] = []
    buckets: Dict[Hashable, List[Any]] = {}

    for geom in geoms:
        key = _bucket_key(geom)
        candidates = buckets.setdefault(key, [])
        if any(_same_point_set(geom, existing) for existing in candidates):
            continue
        candidates.append(geom)
        kept.append(geom)

    return kept


__all__ = ["dedupe_geoms"]