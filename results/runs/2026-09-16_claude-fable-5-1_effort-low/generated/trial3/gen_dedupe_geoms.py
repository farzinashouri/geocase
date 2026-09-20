"""Remove duplicate shapely geometries while preserving first-occurrence order.

Two geometries are considered duplicates when they are topologically equal,
i.e. they describe exactly the same set of points in the plane, regardless of
how their coordinate sequences are written (starting vertex, ring direction,
redundant collinear vertices, polygon vs. equivalent multipolygon, etc.).
"""

from __future__ import annotations

from typing import Iterable, List, Sequence

import shapely
from shapely.geometry.base import BaseGeometry


def _bounds_key(geom: BaseGeometry) -> tuple:
    """Exact bounding-box key. Equal point sets always share identical extreme
    coordinates, so this is a safe (never over-merging) pre-filter."""
    return tuple(geom.bounds)


def dedupe_geoms(geoms: Iterable[BaseGeometry]) -> List[BaseGeometry]:
    """Return a new list with duplicate geometries removed.

    Keeps the first occurrence of each distinct geometry and preserves the
    input order. Duplicates are detected with topological equality
    (``shapely.equals``), so geometries that differ only in coordinate
    ordering, ring orientation, or redundant vertices are treated as equal.

    All empty geometries are considered duplicates of one another (they all
    describe the empty point set). ``None`` entries are kept once.
    """
    result: List[BaseGeometry] = []
    # Bucket kept geometries by exact bounds; only compare within a bucket.
    buckets: dict = {}
    seen_empty = False
    seen_none = False

    for geom in geoms:
        if geom is None:
            if not seen_none:
                seen_none = True
                result.append(geom)
            continue

        if geom.is_empty:
            if not seen_empty:
                seen_empty = True
                result.append(geom)
            continue

        key = _bounds_key(geom)
        bucket: Sequence[BaseGeometry] = buckets.get(key, ())
        if any(shapely.equals(geom, other) for other in bucket):
            continue

        buckets.setdefault(key, []).append(geom)
        result.append(geom)

    return result


__all__ = ["dedupe_geoms"]