"""Deduplicate shapely geometries by the set of points they describe.

Two geometries are duplicates when they cover exactly the same set of points
in the plane, however their coordinates happen to be written: a ring may
start at a different vertex or run in the opposite direction, a line may be
split into a multi-part line, a polygon may list its holes in another order.
Equality is decided topologically by GEOS through ``shapely.equals``.  Empty
geometries all describe the empty set, so they are duplicates of one another
regardless of geometry type.
"""

from __future__ import annotations

from collections.abc import Iterable

import shapely
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]

_EMPTY_KEY: tuple = ("empty",)


def _bucket_key(geom: BaseGeometry) -> tuple:
    """Return a hashable key shared by every geometry with the same point set.

    Geometries describing the same point set necessarily have the same
    extreme coordinates, so the exact ``bounds`` tuple is a lossless
    bucketing key: no arithmetic is involved, only min/max of the stored
    coordinates.  Empty geometries have NaN bounds and get a dedicated key.
    """
    if geom.is_empty:
        return _EMPTY_KEY
    return tuple(geom.bounds)


def dedupe_geoms(geoms: Iterable[BaseGeometry]) -> list[BaseGeometry]:
    """Return a new list of ``geoms`` with topological duplicates removed.

    The first occurrence of each distinct point set is kept, as the original
    object, and input order is preserved.  The input is not modified.

    Raises:
        TypeError: if any item is not a shapely geometry.
    """
    kept: list[BaseGeometry] = []
    # bucket key -> distinct geometries already kept under that key
    buckets: dict[tuple, list[BaseGeometry]] = {}

    for geom in geoms:
        if not isinstance(geom, BaseGeometry):
            raise TypeError(
                f"dedupe_geoms expects shapely geometries, got {type(geom).__name__}"
            )
        key = _bucket_key(geom)
        candidates = buckets.setdefault(key, [])
        if key == _EMPTY_KEY:
            is_duplicate = bool(candidates)
        else:
            is_duplicate = any(
                bool(shapely.equals(geom, other)) for other in candidates
            )
        if not is_duplicate:
            candidates.append(geom)
            kept.append(geom)
    return kept