"""De-duplicate shapely geometries by point-set equality, preserving order.

Two geometries are treated as duplicates when they cover exactly the same set
of points in the plane, regardless of how their coordinates are written down:
a ring may start at a different vertex, wind the other way, carry a Z value, or
be packed into a single-part multi-geometry.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Set, Tuple

import shapely
from shapely.errors import GEOSException
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]


def _exact_key(geom: BaseGeometry) -> bytes:
    """Canonical WKB of ``geom``, flattened to 2D.

    ``shapely.normalize`` rewrites a geometry into GEOS' canonical form: parts
    and rings are ordered, rings start at their lowest vertex and wind in a
    fixed direction. Geometries that differ only in vertex rotation, ring
    direction, part ordering or Z values therefore share a key. Geometries that
    are equal for subtler reasons (redundant collinear vertices, a polygon vs.
    an equivalent one-part multipolygon) do not, so this is only a fast path.
    """
    return shapely.to_wkb(shapely.normalize(shapely.force_2d(geom)))


def _bounds_key(geom: BaseGeometry) -> Tuple[float, float, float, float]:
    """Planar bounding box, which is identical for point-set-equal geometries.

    Adding 0.0 collapses -0.0 and 0.0 so they hash alike.
    """
    return tuple(value + 0.0 for value in geom.bounds)  # type: ignore[return-value]


def _same_point_set(a: BaseGeometry, b: BaseGeometry) -> bool:
    """``a.equals(b)``, reporting False where GEOS refuses to answer.

    GEOS raises on geometry collections and can raise on invalid input. Callers
    have already ruled out representational equality via :func:`_exact_key`, so
    falling back to False keeps such geometries distinct rather than silently
    dropping one.
    """
    try:
        return bool(shapely.equals(a, b))
    except GEOSException:
        return False


def dedupe_geoms(geoms: Iterable[BaseGeometry]) -> List[BaseGeometry]:
    """Return ``geoms`` with duplicate geometries removed.

    The first occurrence of each distinct geometry is kept, in input order, and
    is returned unchanged (never a normalized rewrite of itself). All empty
    geometries denote the empty point set and collapse to a single entry.

    Raises:
        TypeError: if any element is not a shapely geometry.
    """
    result: List[BaseGeometry] = []
    seen_exact: Set[bytes] = set()
    buckets: Dict[Tuple[float, float, float, float], List[BaseGeometry]] = {}
    seen_empty = False

    for geom in geoms:
        if not isinstance(geom, BaseGeometry):
            raise TypeError(f"expected a shapely geometry, got {type(geom).__name__}")

        if geom.is_empty:
            if seen_empty:
                continue
            seen_empty = True
            result.append(geom)
            continue

        key = _exact_key(geom)
        if key in seen_exact:
            continue

        bucket = buckets.setdefault(_bounds_key(geom), [])
        if any(_same_point_set(geom, kept) for kept in bucket):
            # Equality is transitive, so this representation is a known
            # duplicate of whatever the bucket already holds; remember its key
            # to short-circuit identical repeats later in the input.
            seen_exact.add(key)
            continue

        seen_exact.add(key)
        bucket.append(geom)
        result.append(geom)

    return result