"""De-duplicate shapely geometries by the set of points they cover.

``dedupe_geoms`` keeps the first occurrence of each distinct geometry and
preserves input order.  Duplicates are decided by planar point-set equality
(GEOS ``equals``), not by coordinate sequence, so all of these collapse to a
single entry: a ring written from a different starting vertex, a ring wound in
the opposite direction, a ``Polygon`` and the one-part ``MultiPolygon`` that
covers it, a line carrying redundant collinear vertices, and two adjacent
parts versus the single polygon they tile.

Two consequences of comparing point sets rather than coordinates are worth
stating explicitly:

* Comparison is planar -- Z/M values are ignored, so ``POINT Z (0 0 1)`` and
  ``POINT (0 0)`` are duplicates.
* Every empty geometry denotes the empty point set, so at most one empty
  geometry survives, whatever its type.

Cost: a canonical WKB (normalized, forced to 2D) resolves the common cases
with a dict lookup.  Only geometries whose bounding boxes collide exactly fall
back to a GEOS ``equals`` call -- equal point sets always have identical
bounds, so that fallback cannot miss a duplicate, and in practice it runs over
buckets of one or two geometries rather than the whole list.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Set, Tuple

import shapely
from shapely.errors import GEOSException
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]


def dedupe_geoms(geoms: Iterable[BaseGeometry]) -> List[BaseGeometry]:
    """Return a new list holding the first occurrence of each distinct geometry.

    Parameters
    ----------
    geoms
        Iterable of shapely geometries.  The objects themselves are returned
        unchanged; nothing is normalized in place.

    Returns
    -------
    list
        The kept geometries, in input order.

    Raises
    ------
    TypeError
        If an element is not a shapely geometry.
    """
    kept: List[BaseGeometry] = []
    seen_wkb: Set[bytes] = set()
    by_bounds: Dict[Tuple[float, float, float, float], List[BaseGeometry]] = defaultdict(list)
    seen_empty = False

    for index, geom in enumerate(geoms):
        if not isinstance(geom, BaseGeometry):
            raise TypeError(
                f"geoms[{index}] is {type(geom).__name__}, expected a shapely geometry"
            )

        if geom.is_empty:
            if seen_empty:
                continue
            seen_empty = True
            kept.append(geom)
            continue

        wkb = _canonical_wkb(geom)
        if wkb is not None and wkb in seen_wkb:
            continue

        bounds = geom.bounds
        bucket = by_bounds[bounds]
        if any(_same_point_set(geom, other) for other in bucket):
            continue

        kept.append(geom)
        bucket.append(geom)
        if wkb is not None:
            seen_wkb.add(wkb)

    return kept


def _canonical_wkb(geom: BaseGeometry) -> Optional[bytes]:
    """Canonical form of ``geom``; equal bytes guarantee equal point sets.

    ``normalize`` puts rings, ring start vertices, winding order and multi-part
    ordering into a canonical arrangement, and ``force_2d`` drops Z/M so the
    key matches the planar comparison used elsewhere.  Unequal bytes prove
    nothing -- that is what the ``equals`` fallback is for.  Returns ``None``
    when GEOS cannot produce a canonical form, which just disables the fast
    path for that geometry.
    """
    try:
        return shapely.to_wkb(shapely.normalize(shapely.force_2d(geom)))
    except GEOSException:
        return None


def _same_point_set(a: BaseGeometry, b: BaseGeometry) -> bool:
    """``a.equals(b)``, treating a GEOS failure as "not a duplicate".

    ``equals`` can raise on pathological (self-intersecting, non-noded) input.
    Keeping both geometries is the safe outcome: de-duplication stays
    conservative instead of dropping a geometry on an unresolved comparison.
    """
    try:
        return a.equals(b)
    except GEOSException:
        return False