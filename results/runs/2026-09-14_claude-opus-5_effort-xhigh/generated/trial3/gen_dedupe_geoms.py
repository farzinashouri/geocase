"""Order-preserving de-duplication of shapely geometries.

``dedupe_geoms`` keeps the first occurrence of each distinct geometry.  Two
geometries are duplicates when they cover exactly the same set of points in the
plane, however their coordinates happen to be written down: a ring may start at
a different vertex, wind the opposite way, carry redundant collinear vertices,
list the parts of a multi-geometry in another order, or store Z values that a
planar comparison ignores.

The comparison is exact, not approximate: coordinates differing in the last
floating point bit describe different point sets and are kept apart.  Use
``shapely.set_precision`` on the inputs first if you want snapping instead.

Duplicate detection runs in two stages so that the common case stays cheap:

1. Geometries are bucketed by their bounding box, which is identical for every
   representation of the same point set (each extreme is attained at a vertex
   that both geometries must contain).  This is a pure dict lookup.
2. Inside a bucket, a geometry first tries an exact match against the canonical
   (GEOS-normalized) WKB of what has been seen; only if that misses does it
   fall back to a topological ``equals`` against the bucket's kept geometries.

Stage 1 makes the scan linear in the number of distinct bounding boxes; the
quadratic ``equals`` work is confined to geometries that already share a box.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Set, Tuple

import shapely
from shapely.errors import GEOSException
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]

# Empty geometries have undefined (NaN) bounds, which never compare equal, so
# they get one shared bucket instead -- they all describe the empty point set.
_EMPTY_BUCKET = "empty"

# Per bucket: canonical WKBs already accounted for, and the geometries kept.
_Bucket = Tuple[Set[bytes], List[BaseGeometry]]


def _bucket_key(geom: BaseGeometry):
    """Return a hashable key shared by every representation of ``geom``."""
    if geom.is_empty:
        return _EMPTY_BUCKET
    return geom.bounds


def _canonical_wkb(geom: BaseGeometry) -> bytes:
    """Return the WKB of ``geom`` in GEOS normal form.

    Normalizing rewrites rings from a canonical starting vertex with canonical
    orientation and sorts the parts of a collection, so geometries that differ
    only in coordinate ordering collapse to identical bytes.
    """
    return shapely.to_wkb(shapely.normalize(geom))


def _same_points(a: BaseGeometry, b: BaseGeometry) -> bool:
    """Test planar point-set equality, tolerating unprocessable input."""
    try:
        return bool(shapely.equals(a, b))
    except GEOSException:
        # Invalid geometry (a self-intersecting ring, say) can defeat the
        # topology engine.  The canonical-form check has already run, so
        # reporting "not equal" here keeps the geometry rather than dropping
        # something that was never shown to be a duplicate.
        return False


def dedupe_geoms(geoms: Iterable[BaseGeometry]) -> List[BaseGeometry]:
    """Remove duplicate geometries, keeping the first of each and their order.

    Args:
        geoms: Shapely geometries.  Any iterable will do; it is consumed once.

    Returns:
        A new list holding the first occurrence of each distinct geometry, in
        input order.  The geometry objects themselves are returned unchanged
        (not normalized copies).

    Raises:
        TypeError: If an element is not a shapely geometry.
    """
    kept: List[BaseGeometry] = []
    buckets: Dict[object, _Bucket] = {}

    for geom in geoms:
        if not isinstance(geom, BaseGeometry):
            raise TypeError(
                f"expected a shapely geometry, got {type(geom).__name__!r}"
            )

        seen_wkb, bucket_geoms = buckets.setdefault(_bucket_key(geom), (set(), []))
        wkb = _canonical_wkb(geom)

        if wkb in seen_wkb:
            continue
        # Whichever way the check below goes, this exact spelling is covered
        # from now on, so later identical inputs skip the topological test.
        seen_wkb.add(wkb)

        if any(_same_points(geom, other) for other in bucket_geoms):
            continue

        bucket_geoms.append(geom)
        kept.append(geom)

    return kept