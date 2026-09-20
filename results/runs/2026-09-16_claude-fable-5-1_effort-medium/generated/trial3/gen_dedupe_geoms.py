"""Order-preserving de-duplication of shapely geometries.

Two geometries are considered duplicates when they describe exactly the same
set of points in the plane (topological equality), regardless of how their
coordinate sequences are written: different starting vertex, opposite ring
orientation, redundant collinear vertices, a MultiPolygon holding a single
polygon versus that polygon itself, and so on.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

import shapely
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]

_EMPTY_KEY: Tuple = ("__empty__",)


def _bucket_key(geom: BaseGeometry) -> Tuple:
    """Cheap hashable key that is identical for any two point-set-equal geometries.

    Equal point sets have equal envelopes, so exact bounds are a safe bucket key.
    Empty geometries have NaN bounds (which never compare equal), so they get a
    dedicated sentinel key instead.
    """
    if geom.is_empty:
        return _EMPTY_KEY
    return tuple(geom.bounds)


def _canonical_wkb(geom: BaseGeometry) -> Optional[bytes]:
    """Normalized WKB, used as a fast pre-check and as a fallback comparison."""
    try:
        return shapely.to_wkb(shapely.normalize(geom))
    except Exception:  # pragma: no cover - defensive for exotic/invalid input
        return None


def _same_point_set(a: BaseGeometry, b: BaseGeometry) -> bool:
    """True when ``a`` and ``b`` cover exactly the same points in the plane."""
    if a.is_empty and b.is_empty:
        return True
    if a.is_empty or b.is_empty:
        return False

    # Fast path: identical after canonical ordering (catches reversed rings,
    # rotated starting vertices, reordered multi-part members, ...).
    wa, wb = _canonical_wkb(a), _canonical_wkb(b)
    if wa is not None and wa == wb:
        return True

    # Full topological equality (catches redundant vertices, Multi-wrapping of a
    # single part, differently split linework describing the same curve, ...).
    try:
        return bool(shapely.equals(a, b))
    except Exception:
        # GEOS can raise on badly invalid geometries; fall back to the
        # canonical-form comparison already computed above.
        return wa is not None and wa == wb


def dedupe_geoms(geoms: Iterable[BaseGeometry]) -> List[BaseGeometry]:
    """Return a new list with duplicate geometries removed.

    The first occurrence of each distinct point set is kept and the original
    order is preserved. The input is not modified.

    Parameters
    ----------
    geoms:
        Iterable of shapely geometries. ``None`` entries are dropped.

    Returns
    -------
    list
        The retained geometry objects (the original objects, not copies).
    """
    result: List[BaseGeometry] = []
    buckets: dict = {}

    for geom in geoms:
        if geom is None:
            continue
        key = _bucket_key(geom)
        candidates = buckets.setdefault(key, [])
        if any(_same_point_set(kept, geom) for kept in candidates):
            continue
        candidates.append(geom)
        result.append(geom)

    return result