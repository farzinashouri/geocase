"""Order-preserving de-duplication of shapely geometries by point-set equality.

Two geometries are treated as duplicates when they cover exactly the same set of
points in the plane, regardless of how their coordinates are written down: a ring
may start at a different vertex, run in the opposite direction, carry redundant
collinear vertices, or be split differently across the parts of a multi-geometry.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import Any, Iterable, List

import numpy as np
import shapely
from shapely import STRtree
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]


def _canonical_key(geom: BaseGeometry) -> bytes:
    """Cheap exact key: geometries with the same key are certainly identical.

    ``normalize`` puts rings, components and vertex order into a canonical form,
    so most "same shape, different writing" cases collapse here without any
    topology work. A differing key proves nothing, so the caller still runs a
    real ``equals`` pass over the surviving representatives.
    """
    try:
        return shapely.to_wkb(shapely.normalize(geom), include_srid=False)
    except Exception:  # pragma: no cover - defensive: exotic/invalid geometry
        return shapely.to_wkb(geom, include_srid=False)


def _duplicate_pairs(arr: np.ndarray) -> Iterable[tuple[int, int]]:
    """Yield ``(i, j)`` with ``i < j`` for point-set-equal geometries in ``arr``.

    Candidates are narrowed with an STRtree bounding-box query and an exact
    bounds comparison (true duplicates share the same extreme coordinates, so
    this filter is lossless) before the expensive predicate runs.
    """
    if len(arr) < 2:
        return []

    tree = STRtree(arr)
    left, right = tree.query(arr)
    upper = left < right
    left, right = left[upper], right[upper]
    if left.size == 0:
        return []

    bounds = shapely.bounds(arr)
    same_box = np.all(bounds[left] == bounds[right], axis=1)
    left, right = left[same_box], right[same_box]
    if left.size == 0:
        return []

    try:
        equal = shapely.equals(arr[left], arr[right])
    except Exception:  # pragma: no cover - GEOS may refuse some collections
        equal = np.array(
            [_safe_equals(a, b) for a, b in zip(arr[left], arr[right])], dtype=bool
        )

    return zip(left[equal].tolist(), right[equal].tolist())


def _safe_equals(a: BaseGeometry, b: BaseGeometry) -> bool:
    try:
        return bool(shapely.equals(a, b))
    except Exception:
        return False


def dedupe_geoms(geoms: Iterable[Any]) -> List[Any]:
    """Return a new list with duplicate geometries removed, order preserved.

    The first occurrence of each distinct geometry is kept. All empty geometries
    describe the empty point set and therefore collapse to a single entry;
    ``None`` values, if present, are likewise kept once.

    Parameters
    ----------
    geoms:
        Iterable of shapely geometries (``None`` entries are tolerated).

    Returns
    -------
    list
        A new list; the geometry objects themselves are not copied.
    """
    items = list(geoms)
    if len(items) < 2:
        return items

    for pos, geom in enumerate(items):
        if geom is not None and not isinstance(geom, BaseGeometry):
            raise TypeError(
                f"geoms[{pos}] is {type(geom).__name__}, expected a shapely geometry"
            )

    # Partition: None / empty need no geometric comparison at all.
    candidates: List[int] = []
    seen_none = False
    seen_empty = False
    dropped = set()
    for pos, geom in enumerate(items):
        if geom is None:
            if seen_none:
                dropped.add(pos)
            seen_none = True
        elif geom.is_empty:
            if seen_empty:
                dropped.add(pos)
            seen_empty = True
        else:
            candidates.append(pos)

    # Pass 1: exact canonical-form grouping, keeping the earliest position.
    reps: List[int] = []
    by_key: dict[bytes, int] = {}
    for pos in candidates:
        key = _canonical_key(items[pos])
        first = by_key.get(key)
        if first is None:
            by_key[key] = pos
            reps.append(pos)
        else:
            dropped.add(pos)

    # Pass 2: true point-set equality over the surviving representatives, for
    # duplicates whose canonical forms still differ (e.g. redundant vertices,
    # 2D vs 3D coordinates, differently partitioned multi-geometries).
    if len(reps) > 1:
        arr = np.array([items[pos] for pos in reps], dtype=object)
        for i, j in _duplicate_pairs(arr):
            first, later = reps[i], reps[j]
            if first > later:
                first, later = later, first
            dropped.add(later)

    return [geom for pos, geom in enumerate(items) if pos not in dropped]