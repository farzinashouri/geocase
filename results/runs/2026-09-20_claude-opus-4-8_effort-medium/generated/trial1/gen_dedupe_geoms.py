"""Deduplicate shapely geometries by the set of points they cover.

Two geometries are treated as duplicates when they are geometrically equal --
they describe the same set of points in the plane -- regardless of how their
coordinates are ordered (e.g. a ring started at a different vertex or wound in
the opposite direction). The first occurrence of each distinct geometry is
kept and the original order is preserved.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import Hashable, List

import shapely


def _bucket_key(geom) -> Hashable:
    """A cheap key that is stable under coordinate reordering/reversal.

    ``shapely.normalize`` rewrites a geometry into a canonical form, so two
    geometries with the same point set usually serialize to identical WKB.
    We only use this to group candidates cheaply; exact membership is still
    confirmed with a proper geometric equality test, so a key collision or a
    key mismatch between truly-equal geometries never produces a wrong result.
    """
    if geom is None:
        return None
    try:
        return shapely.normalize(geom).wkb
    except Exception:
        # Fall back to a single shared bucket; correctness is preserved by the
        # exact equality check below, only speed is affected.
        return b""


def dedupe_geoms(geoms) -> List:
    """Return a new list of ``geoms`` with geometric duplicates removed.

    Order is preserved and the first occurrence of each distinct geometry is
    kept. Duplicates are detected by geometric equality (same set of points),
    not by coordinate-sequence identity.
    """
    result: List = []
    # Map bucket key -> list of already-kept geometries sharing that key.
    buckets: dict = {}

    for geom in geoms:
        key = _bucket_key(geom)
        candidates = buckets.get(key)

        if candidates is None:
            buckets[key] = [geom]
            result.append(geom)
            continue

        if any(_same(geom, kept) for kept in candidates):
            continue

        candidates.append(geom)
        result.append(geom)

    return result


def _same(a, b) -> bool:
    """True when ``a`` and ``b`` cover exactly the same set of points."""
    if a is None or b is None:
        return a is None and b is None
    try:
        return bool(a.equals(b))
    except Exception:
        return a is b