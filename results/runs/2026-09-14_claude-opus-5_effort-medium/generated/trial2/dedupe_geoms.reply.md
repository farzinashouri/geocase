```python
"""Order-preserving de-duplication of shapely geometries.

Two geometries count as duplicates when they cover exactly the same set of
points in the plane, regardless of how their coordinate sequences are written
(different ring start vertex, reversed orientation, redundant collinear
vertices, a polygon expressed as a single part vs. an equivalent multi-part
geometry, ...).
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

import shapely
from shapely.errors import GEOSException

__all__ = ["dedupe_geoms"]


def _canonical_wkb(geom: Any) -> bytes:
    """Canonical byte form of a geometry: identical bytes imply identical point sets.

    ``shapely.normalize`` rewrites rings to a canonical start vertex and
    orientation and sorts the parts of multi-part geometries, so this catches
    the common cases cheaply. The converse does not hold (e.g. redundant
    collinear vertices), so a byte mismatch falls through to ``equals``.
    """
    return shapely.to_wkb(shapely.normalize(geom))


def _same_points(a: Any, b: Any) -> bool:
    """True when ``a`` and ``b`` describe the same set of points."""
    try:
        return bool(shapely.equals(a, b))
    except GEOSException:
        # GEOS refuses the ``equals`` predicate on geometry collections.
        return _canonical_wkb(a) == _canonical_wkb(b)


def dedupe_geoms(geoms: Iterable[Any]) -> List[Any]:
    """Return the geometries with duplicates removed, first occurrence kept.

    Order is preserved. Duplicates are decided by point-set equality, not by
    coordinate sequence. All empty geometries are mutually equal (they all
    cover the empty set) and collapse to the first one seen. ``None`` entries
    are passed through and deduplicated among themselves.
    """
    out: List[Any] = []

    # Equal point sets always have equal bounds, so bounds are a safe bucket
    # key: only geometries sharing a bucket can possibly be duplicates.
    buckets: Dict[Tuple[float, float, float, float], List[Tuple[bytes, Any]]] = {}
    seen_empty = False
    seen_none = False

    for geom in geoms:
        if geom is None:
            if seen_none:
                continue
            seen_none = True
            out.append(geom)
            continue

        if geom.is_empty:
            # Empty bounds contain NaN and cannot be used as a dict key.
            if seen_empty:
                continue
            seen_empty = True
            out.append(geom)
            continue

        bucket = buckets.setdefault(geom.bounds, [])
        key = _canonical_wkb(geom)

        duplicate = False
        for other_key, other in bucket:
            if key == other_key or _same_points(geom, other):
                duplicate = True
                break
        if duplicate:
            continue

        bucket.append((key, geom))
        out.append(geom)

    return out
```