```python
"""Order-preserving de-duplication of shapely geometries by point-set identity.

Two geometries are treated as duplicates when they cover exactly the same set
of points in the plane, regardless of how their coordinates are written down:
a ring starting at a different vertex, a reversed orientation, extra collinear
vertices, or a differently nested multi-part structure all compare equal.
Z values are ignored, since identity is defined in the plane.

All empty geometries denote the empty point set and therefore collapse to a
single representative.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

import shapely
from shapely import STRtree
from shapely.errors import GEOSException, ShapelyError
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]


def _normalized_key(geom: BaseGeometry) -> Optional[bytes]:
    """A canonical byte key, or None if the geometry cannot be canonicalised.

    Equal keys imply equal point sets, so the key is a sound fast path for
    accepting a duplicate. Unequal keys imply nothing, so a key miss must fall
    through to a real topological comparison.
    """
    try:
        return shapely.to_wkb(shapely.normalize(geom), include_srid=False)
    except (GEOSException, ShapelyError, ValueError):
        return None


def _same_point_set(a: BaseGeometry, b: BaseGeometry) -> bool:
    """Topological equality, degrading to canonical-form equality on failure."""
    try:
        return bool(shapely.equals(a, b))
    except (GEOSException, ShapelyError):
        # Invalid input (self-intersecting rings, NaN coordinates, ...) can make
        # GEOS refuse the predicate; fall back to the strictest sound test.
        key_a = _normalized_key(a)
        return key_a is not None and key_a == _normalized_key(b)


def dedupe_geoms(geoms: Iterable[BaseGeometry]) -> List[BaseGeometry]:
    """Return a new list of ``geoms`` with duplicate geometries removed.

    The first occurrence of each distinct geometry is kept and the relative
    order of the kept geometries matches the input order. The input is not
    modified and the kept geometry objects are the original objects, not copies.

    Parameters
    ----------
    geoms:
        Iterable of shapely geometries.

    Returns
    -------
    list
        The de-duplicated geometries, in first-occurrence order.

    Raises
    ------
    TypeError
        If any element is not a shapely geometry.
    """
    items = list(geoms)
    for i, geom in enumerate(items):
        if not isinstance(geom, BaseGeometry):
            raise TypeError(
                f"geoms[{i}] is {type(geom).__name__}, expected a shapely geometry"
            )
    if not items:
        return []

    # Equal geometries always have intersecting envelopes, so an envelope query
    # is a sound (superset) prefilter: it can only ever return too many
    # candidates, never drop a true duplicate.
    tree = STRtree(items)

    kept_indices: List[int] = []
    is_kept = [False] * len(items)
    keys: dict[bytes, int] = {}
    have_empty = False

    for i, geom in enumerate(items):
        if geom.is_empty:
            if have_empty:
                continue
            have_empty = True
            is_kept[i] = True
            kept_indices.append(i)
            continue

        key = _normalized_key(geom)
        if key is not None and key in keys:
            continue

        duplicate = False
        for j in tree.query(geom):
            j = int(j)
            if j >= i or not is_kept[j]:
                continue
            if _same_point_set(geom, items[j]):
                duplicate = True
                break
        if duplicate:
            continue

        if key is not None:
            keys[key] = i
        is_kept[i] = True
        kept_indices.append(i)

    return [items[i] for i in kept_indices]
```