```python
"""De-duplicate shapely geometries by point-set equality, preserving order.

`dedupe_geoms` keeps the first occurrence of each distinct geometry, where two
geometries count as the same when they cover exactly the same set of points in
the plane.  That is a *topological* comparison, not a comparison of coordinate
sequences: a ring written from a different starting vertex, wound the opposite
way, carrying redundant collinear vertices, or differing only in Z values all
collapse onto a single representative.

The work is done in two stages so that the expensive predicate runs rarely:

1.  Geometries are bucketed by their bounding box.  The bounding box is a
    function of the point set alone, so equal geometries always land in the
    same bucket and only geometries sharing a bucket can possibly be equal.
2.  Within a bucket, a canonical WKB (GEOS `normalize`, forced to 2D) gives an
    O(1) hash hit for the common case of geometries that differ only in vertex
    order/orientation.  Anything that misses falls back to `equals`, which is
    authoritative for the remaining cases that no canonical form catches.

Empty geometries all describe the empty point set, so they are treated as
duplicates of one another regardless of their geometry type (GEOS `equals`
reports False for them, since its DE-9IM pattern requires interiors to meet).
"""

from __future__ import annotations

from typing import Iterable, List

import shapely
from shapely.errors import GEOSException
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]


def _canonical_wkb(geom: BaseGeometry) -> bytes:
    """Return a byte string equal for geometries with equal normalized form."""
    return shapely.to_wkb(shapely.normalize(geom), output_dimension=2)


def _same_points(a: BaseGeometry, b: BaseGeometry) -> bool:
    """True when `a` and `b` cover the same set of points in the plane."""
    try:
        return bool(shapely.equals(a, b))
    except GEOSException:
        # Invalid input can make the overlay-based predicate fail; the callers
        # have already ruled out canonical-form equality, so report distinct
        # rather than dropping a geometry we cannot confidently compare.
        return False


def dedupe_geoms(geoms: Iterable[BaseGeometry]) -> List[BaseGeometry]:
    """Return the geometries of `geoms` with duplicates removed.

    The first occurrence of each distinct geometry is kept and the input order
    of those survivors is preserved.  Two geometries are duplicates when they
    describe the same set of points, however their coordinates are written.

    Parameters
    ----------
    geoms
        An iterable of shapely geometries.  It is consumed once.

    Returns
    -------
    list
        A new list holding the kept geometry objects themselves (not copies).

    Raises
    ------
    TypeError
        If any element is not a shapely geometry.
    """
    kept: List[BaseGeometry] = []
    # bounds -> (canonical WKBs already resolved, distinct geometries kept)
    buckets: dict[tuple, tuple[set, List[BaseGeometry]]] = {}
    seen_empty = False

    for geom in geoms:
        if not isinstance(geom, BaseGeometry):
            raise TypeError(
                f"expected a shapely geometry, got {type(geom).__name__}"
            )

        if geom.is_empty:
            # Empty bounds are NaN-filled and unusable as a dict key, and every
            # empty geometry denotes the same (empty) point set.
            if seen_empty:
                continue
            seen_empty = True
            kept.append(geom)
            continue

        seen_wkb, bucket_geoms = buckets.setdefault(geom.bounds, (set(), []))
        wkb = _canonical_wkb(geom)

        if wkb in seen_wkb:
            continue

        # Record the canonical form either way: it memoizes this exact vertex
        # layout, whether or not the geometry itself turns out to be new.
        seen_wkb.add(wkb)

        if any(_same_points(geom, other) for other in bucket_geoms):
            continue

        bucket_geoms.append(geom)
        kept.append(geom)

    return kept
```