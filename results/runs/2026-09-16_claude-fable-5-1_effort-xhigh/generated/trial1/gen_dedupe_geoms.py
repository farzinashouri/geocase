"""Order-preserving deduplication of shapely geometries by the point set they cover.

Two geometries are duplicates when they describe exactly the same set of points
in the plane, regardless of how the coordinates are written: a ring started at
a different vertex or traced in the opposite direction, parts of a multi-part
geometry listed in a different order, redundant collinear vertices, or even a
different geometry type for the same shape (a one-part MultiPolygon versus the
Polygon itself, a MultiPoint of one point versus that Point).
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

import shapely
from shapely.errors import GEOSException

__all__ = ["dedupe_geoms"]

# Every empty geometry covers the same (empty) point set. They share this key
# because their NaN bounds would never compare or hash as equal.
_EMPTY_KEY: Tuple[str] = ("__empty__",)


def _bucket_key(geom: Any) -> Tuple[Any, ...]:
    """Return a hashable key that is identical for any two geometries with equal point sets.

    A geometry's envelope depends only on the set of points it covers, and the
    envelope corners always lie on stored vertices, so two geometries covering
    the same points have bit-identical bounds. Different point sets may still
    share a key; the bucket contents are compared exactly afterwards.
    """
    if geom.is_empty:
        return _EMPTY_KEY
    return tuple(geom.bounds)


def _canonical_wkb(geom: Any) -> bytes:
    """WKB of the GEOS-normalized geometry: canonical ring start, orientation and part order."""
    return shapely.to_wkb(shapely.normalize(geom))


def _same_point_set(a: Any, a_wkb: bytes, b: Any, b_wkb: bytes) -> bool:
    """True when ``a`` and ``b`` cover exactly the same points in the plane."""
    if a_wkb == b_wkb:
        # Structurally identical after normalization: cheap exact match that
        # already covers reversed rings, rotated start vertices and reordered parts.
        return True
    try:
        # Topological equality (DE-9IM ``T*F**FFF*``) catches everything the
        # structural test misses, such as redundant collinear vertices or a
        # Polygon versus an equivalent single-part MultiPolygon.
        return bool(shapely.equals(a, b))
    except GEOSException:
        # Topology could not be computed (badly invalid input). The canonical
        # forms already differ, so treat the geometries as distinct.
        return False


def dedupe_geoms(geoms: Iterable[Any]) -> List[Any]:
    """Return ``geoms`` with duplicates removed, keeping the first occurrence of each.

    Order is preserved and the original geometry objects are returned (never
    normalized copies). Duplicates are geometries that cover exactly the same
    set of points in the plane, even when their coordinate sequences differ.
    """
    buckets: Dict[Any, List[Tuple[Any, bytes]]] = {}
    result: List[Any] = []

    for geom in geoms:
        if geom is None:
            key: Any = None
            wkb = b""
        else:
            key = _bucket_key(geom)
            wkb = _canonical_wkb(geom)

        bucket = buckets.setdefault(key, [])
        if any(_same_point_set(geom, wkb, kept, kept_wkb) for kept, kept_wkb in bucket):
            continue

        bucket.append((geom, wkb))
        result.append(geom)

    return result