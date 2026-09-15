"""Order-preserving de-duplication of shapely geometries by point-set equality.

Two geometries count as duplicates when they cover exactly the same set of points
in the plane, however their coordinates happen to be spelled: a ring may start at
a different vertex or wind the other way, a line may carry redundant repeated or
collinear vertices, a shape may be split into a different number of parts
(``LineString`` vs. ``MultiLineString``), and Z/M values are ignored because the
comparison is planar.

Equality is exact -- there is no distance tolerance.  Coordinates differing in the
last floating point digit describe different point sets, so snap the inputs with
``shapely.set_precision`` first if that is not what you want.
"""

from __future__ import annotations

from collections.abc import Iterable

import shapely
from shapely.errors import GEOSException
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]


def dedupe_geoms(geoms: Iterable[BaseGeometry]) -> list[BaseGeometry]:
    """Return the geometries of *geoms* with duplicate point sets dropped.

    The first occurrence of each distinct point set is kept, in input order, and
    the result holds the original geometry objects -- never rewritten copies.  All
    empty geometries describe the empty point set, so they collapse to a single
    entry whatever their type.

    Raises:
        TypeError: if an element is not a shapely geometry.
    """
    unique: list[BaseGeometry] = []
    # Bucket key -> (canonical spellings already resolved, representatives kept).
    buckets: dict[object, tuple[set[bytes], list[BaseGeometry]]] = {}

    for index, geom in enumerate(geoms):
        if not isinstance(geom, BaseGeometry):
            raise TypeError(
                f"geoms[{index}] is {type(geom).__name__}, not a shapely geometry"
            )

        seen, representatives = buckets.setdefault(_bucket_key(geom), (set(), []))
        canonical = _canonical_wkb(geom)
        if canonical in seen:
            continue

        duplicate = any(_same_point_set(geom, rep) for rep in representatives)
        # Remember this spelling either way: a later geometry written the same
        # way resolves the same way, without re-running the predicate.
        seen.add(canonical)
        if not duplicate:
            unique.append(geom)
            representatives.append(geom)

    return unique


def _bucket_key(geom: BaseGeometry) -> object:
    """Group geometries that could possibly be duplicates of one another.

    Geometries covering the same points have the same bounding box, because the
    extreme coordinate of a point, line or polygon is always attained at a vertex
    and both spellings therefore contain it.  Comparing only within a bounds group
    keeps the pairwise work tiny without ever splitting a true duplicate pair.
    Empty geometries have no meaningful bounds and share one group.
    """
    return None if geom.is_empty else geom.bounds


def _canonical_wkb(geom: BaseGeometry) -> bytes:
    """Return WKB for *geom* in GEOS normal form, flattened to two dimensions.

    Normal form fixes ring orientation, the ring start vertex and the order of the
    parts of a multi-part geometry, so the usual re-spellings of one shape hash to
    identical bytes.  It does not drop redundant vertices, which is why this is a
    fast path in front of :func:`_same_point_set` rather than a replacement for it.
    """
    flat = shapely.force_2d(geom)
    return shapely.to_wkb(shapely.normalize(flat), output_dimension=2)


def _same_point_set(a: BaseGeometry, b: BaseGeometry) -> bool:
    """Return whether *a* and *b* cover exactly the same points in the plane."""
    if a.is_empty and b.is_empty:
        return True
    try:
        return bool(shapely.equals(a, b))
    except GEOSException:
        # Older GEOS refuses ``equals`` on GeometryCollection arguments, and an
        # invalid geometry can raise mid-predicate.  Fall back to comparing
        # canonical spellings: still exact, just stricter than the predicate, so
        # two spellings of one collection may survive as separate entries.
        return _canonical_wkb(a) == _canonical_wkb(b)