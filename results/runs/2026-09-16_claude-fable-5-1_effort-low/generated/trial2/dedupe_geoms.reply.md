```python
"""Deduplicate shapely geometries by the point set they describe.

Two geometries are duplicates when they cover exactly the same set of
points in the plane, regardless of how their coordinate sequences are
written (starting vertex, winding direction, redundant collinear vertices,
part ordering in multi-geometries, etc.).
"""

from __future__ import annotations

from typing import Iterable, List, Optional, TypeVar

import shapely
from shapely.geometry.base import BaseGeometry

G = TypeVar("G", bound=BaseGeometry)


def _canonical_key(geom: BaseGeometry) -> Optional[str]:
    """Return a hashable key that is identical for point-set-equal geometries.

    Uses shapely's normalize() (canonical vertex order, orientation, and
    part ordering) after removing redundant collinear vertices via
    simplify(0). Returns None if the geometry cannot be canonicalised so
    the caller can fall back to pairwise topological comparison.
    """
    try:
        g = geom
        if not g.is_empty:
            # Zero-tolerance simplify drops collinear/duplicate vertices without
            # changing the point set, so rings written with extra vertices
            # match rings written without them.
            simplified = shapely.simplify(g, 0.0, preserve_topology=True)
            if simplified is not None and not simplified.is_empty:
                g = simplified
        g = shapely.normalize(g)
        return f"{g.geom_type}|{shapely.to_wkb(g, hex=True)}"
    except Exception:
        return None


def dedupe_geoms(geoms: Iterable[G]) -> List[G]:
    """Remove duplicate geometries, keeping the first occurrence in order.

    Duplicates are geometries describing exactly the same set of points,
    determined via topological equality (``shapely.equals``), which ignores
    coordinate ordering, ring start vertex, orientation, and redundant
    vertices. A canonical-form hash is used as a fast path; anything that
    cannot be hashed falls back to pairwise ``equals`` checks.
    """
    result: List[G] = []
    seen_keys: set = set()
    unkeyed: List[BaseGeometry] = []

    for geom in geoms:
        if geom is None:
            if not any(g is None for g in result):
                result.append(geom)  # type: ignore[arg-type]
            continue

        key = _canonical_key(geom)
        if key is not None:
            if key in seen_keys:
                continue
            # Guard against rare cases where normalize yields different
            # bytes for topologically equal inputs (e.g. floating noise):
            # verify against already-kept geometries with the same bounds.
            if any(
                kept is not None
                and kept.geom_type == geom.geom_type
                and kept.bounds == geom.bounds
                and shapely.equals(kept, geom)
                for kept in result
            ):
                seen_keys.add(key)
                continue
            seen_keys.add(key)
            result.append(geom)
        else:
            if any(shapely.equals(kept, geom) for kept in result if kept is not None):
                continue
            unkeyed.append(geom)
            result.append(geom)

    return result


__all__ = ["dedupe_geoms"]
```