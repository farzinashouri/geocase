```python
"""Order-preserving de-duplication of shapely geometries.

``dedupe_geoms`` treats two geometries as duplicates when they describe exactly
the same set of points in the plane.  That is a stronger notion than comparing
coordinate sequences: a ring written from a different starting vertex, wound the
opposite way, or carrying extra collinear vertices is still recognised as a
repeat of the geometry that came before it.

Comparison is planar -- Z and M values are ignored, which is how the underlying
GEOS predicates behave too.  ``None`` is accepted as the "missing geometry"
sentinel that shapely 2 and GeoPandas use; missing values dedupe against each
other, and since every empty geometry describes the same (empty) point set,
empties dedupe against each other regardless of their type.

Strategy: geometries are bucketed by bounding box.  Identical point sets always
have identical bounds, so the bucket key can only ever separate geometries that
genuinely differ.  Within a bucket a canonical WKB form (GEOS ``normalize``)
settles the common cases by hash lookup, and only candidates that share a
bounding box while looking different fall through to the full ``equals``
predicate.
"""

from __future__ import annotations

from typing import Hashable, Iterable

import shapely
from shapely.errors import GEOSException
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]

# Stand-ins for a bounding box / canonical form.  They are bytes so they can
# never collide with a real bounds tuple or a real WKB payload.
_MISSING = b"\x00missing"
_EMPTY = b"\x00empty"
_NAN_BOUNDS = b"\x00nan-bounds"


def dedupe_geoms(geoms: Iterable[BaseGeometry | None]) -> list[BaseGeometry | None]:
    """Return a new list holding the first occurrence of each distinct geometry.

    Input order is preserved and the input geometries are returned unchanged --
    the canonical forms used for comparison are built on copies.

    Args:
        geoms: Geometries to filter.  ``None`` entries are allowed and are
            treated as a single distinct "missing" value.

    Returns:
        A new list with later duplicates dropped.

    Raises:
        TypeError: If an entry is neither a shapely geometry nor ``None``.
    """
    buckets: dict[Hashable, list[tuple[bytes, BaseGeometry | None]]] = {}
    unique: list[BaseGeometry | None] = []

    for index, geom in enumerate(geoms):
        if geom is not None and not isinstance(geom, BaseGeometry):
            raise TypeError(
                f"geoms[{index}] is a {type(geom).__name__}, "
                "expected a shapely geometry or None"
            )

        key, canonical = _fingerprint(geom)
        bucket = buckets.setdefault(key, [])
        if _seen_before(geom, canonical, bucket):
            continue

        bucket.append((canonical, geom))
        unique.append(geom)

    return unique


def _fingerprint(geom: BaseGeometry | None) -> tuple[Hashable, bytes]:
    """Return ``(bucket_key, canonical_form)`` for *geom*.

    Geometries with different bucket keys can never cover the same points, and
    geometries with the same canonical form always do.  Anything in between is
    left for :func:`_equals` to decide.
    """
    if geom is None:
        return _MISSING, _MISSING
    if geom.is_empty:
        return _EMPTY, _EMPTY

    bounds = geom.bounds
    if any(coord != coord for coord in bounds):  # NaN never compares equal
        bounds = _NAN_BOUNDS

    # ``normalize`` puts rings into a fixed winding order starting at their
    # lowest vertex and sorts collection members, so two spellings of the same
    # ring collapse onto identical bytes.  ``force_2d`` keeps the comparison
    # planar, in step with ``equals`` below.
    canonical = shapely.to_wkb(shapely.normalize(shapely.force_2d(geom)))
    return bounds, canonical


def _seen_before(
    geom: BaseGeometry | None,
    canonical: bytes,
    bucket: list[tuple[bytes, BaseGeometry | None]],
) -> bool:
    """Is *geom* already represented in *bucket*?"""
    for kept_canonical, _kept in bucket:
        if kept_canonical == canonical:
            return True

    # Same footprint but written differently enough to survive normalization --
    # e.g. a redundant collinear vertex, or a LineString against the
    # MultiLineString holding only it.  Only the real predicate can tell those
    # apart from genuinely different geometries.
    return any(_equals(geom, kept) for _kept_canonical, kept in bucket)


def _equals(geom: BaseGeometry | None, other: BaseGeometry | None) -> bool:
    """``shapely.equals`` that reports "different" instead of raising."""
    try:
        return bool(shapely.equals(geom, other))
    except GEOSException:
        # Invalid input (self-intersecting rings and friends) can make the
        # overlay engine give up.  Keeping the geometry loses nothing; dropping
        # one that was not proven equal would.
        return False
```