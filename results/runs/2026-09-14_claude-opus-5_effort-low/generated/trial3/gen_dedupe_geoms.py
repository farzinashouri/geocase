"""Deduplicate shapely geometries by point-set equality.

Two geometries are considered duplicates when they cover exactly the same set
of points in the plane, regardless of how their coordinate sequences are
written (different starting vertex, reversed winding, different but equivalent
geometry type, ...).

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import Iterable, List

import shapely
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]


def _canonical_key(geom: BaseGeometry) -> bytes:
    """A cheap canonical form: identical keys imply identical point sets.

    Different keys do *not* imply different point sets, so this is only used as
    a fast path; ``shapely.equals`` decides the remaining cases.
    """
    return shapely.to_wkb(shapely.normalize(geom), flavor="iso")


def dedupe_geoms(geoms: Iterable[BaseGeometry]) -> List[BaseGeometry]:
    """Return the geometries with duplicates removed, first occurrence kept.

    Order of the surviving geometries is the order they first appeared in
    ``geoms``. Duplicates are decided by point-set equality
    (``shapely.equals``), so a ring written from another starting vertex or in
    the opposite direction is recognised as a duplicate.

    ``None`` entries are treated as a single distinct value and collapsed like
    any other duplicate.
    """
    geoms = list(geoms)

    kept: List[BaseGeometry] = []
    seen_keys: dict[bytes, int] = {}
    seen_none = False
    # Indices into ``kept`` that still need an equals() comparison, grouped by
    # nothing in particular; the STRtree below narrows them by bounding box.
    for geom in geoms:
        if geom is None:
            if seen_none:
                continue
            seen_none = True
            kept.append(geom)
            continue

        if not isinstance(geom, BaseGeometry):
            raise TypeError(f"expected a shapely geometry, got {type(geom)!r}")

        key = _canonical_key(geom)
        if key in seen_keys:
            continue

        if geom.is_empty:
            # GEOS predicates report empty == empty as False, so empty
            # geometries are deduped on their canonical form alone.
            seen_keys[key] = len(kept)
            kept.append(geom)
            continue

        if _has_equal(kept, geom):
            continue

        seen_keys[key] = len(kept)
        kept.append(geom)

    return kept


def _has_equal(kept: List[BaseGeometry], geom: BaseGeometry) -> bool:
    """True if ``geom`` is point-set equal to something already in ``kept``."""
    candidates = [
        g
        for g in kept
        if g is not None and not g.is_empty and _bounds_overlap(g, geom)
    ]
    if not candidates:
        return False
    return bool(shapely.equals(shapely.geometrycollections([]) if False else
                               shapely.from_wkb(shapely.to_wkb(geom)),
                               candidates).any())


def _bounds_overlap(a: BaseGeometry, b: BaseGeometry) -> bool:
    """Bounding-box prefilter; equal point sets have equal bounds."""
    return a.bounds == b.bounds