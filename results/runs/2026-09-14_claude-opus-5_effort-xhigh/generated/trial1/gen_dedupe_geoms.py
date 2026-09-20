"""De-duplicate shapely geometries by point-set identity, preserving order.

Two geometries are treated as duplicates when they cover exactly the same set
of points in the plane, regardless of how their coordinate sequences are
written: a ring may start at a different vertex, wind the other way, carry
extra collinear vertices, or be split across a different number of parts.
"""

from __future__ import annotations

from typing import Iterable, List

import shapely
from shapely.errors import GEOSException
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]


def _canonical_wkb(geom: BaseGeometry) -> bytes:
    """Return canonical 2-D WKB for *geom*; equal bytes imply equal point sets.

    ``normalize`` rewrites each ring from a canonical start vertex in a
    canonical direction and sorts the parts of multi-part geometries, so the
    usual "same ring, different winding or start vertex" duplicates collapse to
    byte-identical output. Z/M values are dropped because the comparison is
    planar. The reverse does not hold -- geometries with different vertex
    counts describe the same point set -- so this is only a fast path.
    """
    return shapely.to_wkb(shapely.normalize(geom), output_dimension=2)


def _equals(a: BaseGeometry, b: BaseGeometry) -> bool:
    """Topological (point-set) equality, tolerant of geometries GEOS rejects."""
    try:
        return bool(shapely.equals(a, b))
    except GEOSException:
        # Self-intersecting or otherwise invalid input can make the overlay
        # throw. Such a pair is not byte-identical either, so keep both rather
        # than dropping data on an error.
        return False


def dedupe_geoms(geoms: Iterable[BaseGeometry]) -> List[BaseGeometry]:
    """Return a new list of *geoms* with duplicates removed.

    The first occurrence of each distinct geometry is kept and input order is
    preserved. Duplicates are decided by point-set equality, not by coordinate
    sequence, so a polygon and the same polygon written backwards collapse to
    one entry. All empty geometries describe the empty point set and therefore
    collapse to a single entry as well.

    Raises:
        TypeError: if any element is not a shapely geometry.
    """
    unique: List[BaseGeometry] = []
    seen_wkb: set[bytes] = set()
    # Point-set-equal geometries have bitwise-identical bounds (the extreme
    # coordinates are the same values, no arithmetic involved), so bounds
    # partition the kept geometries into buckets that can never cross-match.
    # Only within a bucket is the expensive GEOS predicate needed.
    by_bounds: dict[tuple, List[BaseGeometry]] = {}
    empty_kept = False

    for geom in geoms:
        if not isinstance(geom, BaseGeometry):
            raise TypeError(
                f"expected a shapely geometry, got {type(geom).__name__}"
            )

        if geom.is_empty:
            if empty_kept:
                continue
            empty_kept = True
            unique.append(geom)
            continue

        key = _canonical_wkb(geom)
        if key in seen_wkb:
            continue

        bucket = by_bounds.setdefault(geom.bounds, [])
        if any(_equals(geom, kept) for kept in bucket):
            continue

        seen_wkb.add(key)
        bucket.append(geom)
        unique.append(geom)

    return unique