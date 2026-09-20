```python
"""De-duplicate shapely geometries by point-set equality.

Two geometries are considered duplicates when they cover exactly the same set
of points in the plane, regardless of how that set is written down: a ring may
start at a different vertex or run in the opposite direction, a line may carry
redundant collinear vertices, and a multi-part geometry may list its parts in a
different order.

Comparison is purely 2-D (X/Y); Z and M values are ignored, matching GEOS
predicate semantics.  All empty geometries denote the empty point set and
therefore collapse into a single representative.
"""

from __future__ import annotations

from typing import Iterable, Iterator

import shapely
from shapely.geometry.base import BaseGeometry, BaseMultipartGeometry

__all__ = ["dedupe_geoms"]


def dedupe_geoms(geoms: Iterable[BaseGeometry]) -> list[BaseGeometry]:
    """Return the geometries with duplicates removed, first occurrence kept.

    Order of the surviving geometries follows the input order, and the objects
    returned are the input objects themselves (no copying, no normalization).

    Args:
        geoms: An iterable of shapely geometries.

    Returns:
        A new list holding one geometry per distinct point set.

    Raises:
        TypeError: If an element is not a shapely geometry.
    """
    unique: list[BaseGeometry] = []
    # Exact-bounds buckets; equal point sets always share exactly equal bounds,
    # so only geometries within a bucket can possibly be duplicates.
    buckets: dict[tuple, list[int]] = {}
    # Fast path: identical normalized WKB implies an identical point set.
    seen_wkb: set[bytes] = set()
    seen_empty = False

    for geom in geoms:
        if not isinstance(geom, BaseGeometry):
            raise TypeError(f"expected a shapely geometry, got {type(geom).__name__}")

        if geom.is_empty:
            if seen_empty:
                continue
            seen_empty = True
            unique.append(geom)
            continue

        wkb = shapely.to_wkb(shapely.normalize(geom))
        if wkb in seen_wkb:
            continue
        seen_wkb.add(wkb)

        key = (shapely.get_dimensions(geom), geom.bounds)
        bucket = buckets.setdefault(key, [])
        if any(_same_point_set(geom, unique[i]) for i in bucket):
            continue

        bucket.append(len(unique))
        unique.append(geom)

    return unique


def _same_point_set(a: BaseGeometry, b: BaseGeometry) -> bool:
    """Test whether two geometries cover the same points in the plane."""
    # GEOS predicates reject heterogeneous collections, so those are compared
    # through a canonical per-dimension decomposition instead.
    if a.geom_type == "GeometryCollection" or b.geom_type == "GeometryCollection":
        return all(
            _equals(x, y) for x, y in zip(_canonical_parts(a), _canonical_parts(b))
        )
    return _equals(a, b)


def _equals(a: BaseGeometry, b: BaseGeometry) -> bool:
    """``shapely.equals`` with well-defined behaviour for empty geometries."""
    if a.is_empty or b.is_empty:
        return a.is_empty and b.is_empty
    return bool(shapely.equals(a, b))


def _canonical_parts(geom: BaseGeometry) -> tuple[BaseGeometry, ...]:
    """Split a point set into its areal, linear and puntal components.

    Each component is unioned and then stripped of anything already covered by
    a higher-dimensional component, so the result depends only on the point set
    and not on how the geometry was assembled.
    """
    by_dim: tuple[list[BaseGeometry], ...] = ([], [], [])
    for part in _iter_atoms(geom):
        by_dim[shapely.get_dimensions(part)].append(part)

    areal = shapely.union_all(by_dim[2])
    linear = shapely.difference(shapely.union_all(by_dim[1]), areal)
    puntal = shapely.difference(
        shapely.union_all(by_dim[0]), shapely.union_all([areal, linear])
    )
    return areal, linear, puntal


def _iter_atoms(geom: BaseGeometry) -> Iterator[BaseGeometry]:
    """Yield the non-empty, single-part geometries nested inside ``geom``."""
    if geom.is_empty:
        return
    if isinstance(geom, BaseMultipartGeometry):
        for part in geom.geoms:
            yield from _iter_atoms(part)
    else:
        yield geom
```