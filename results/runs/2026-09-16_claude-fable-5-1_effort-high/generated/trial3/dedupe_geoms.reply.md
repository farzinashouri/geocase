```python
"""Remove duplicate shapely geometries while preserving first-occurrence order.

Two geometries count as duplicates when they describe exactly the same set of
points in the plane, regardless of how their coordinate sequences are written
(different starting vertex, reversed ring direction, redundant collinear
vertices, Point vs. single-member MultiPoint, ...).  Topological equality
(``shapely.equals``) is the comparison, so the semantics match GEOS.

To avoid an O(n^2) sweep, candidates are bucketed by their exact bounding box:
geometries covering the same point set necessarily share identical bounds, so a
full ``equals`` check is only run against earlier geometries in the same bucket.
"""

from __future__ import annotations

from typing import Hashable, Iterable, List

import shapely
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]


def _bucket_key(geom: BaseGeometry) -> Hashable:
    """Key that is identical for any two geometries with the same point set."""
    if geom.is_empty:
        return ("empty",)
    return ("bounds",) + tuple(geom.bounds)


def _canonical_wkb(geom: BaseGeometry) -> bytes:
    """Structural fallback used only when GEOS cannot evaluate ``equals``."""
    return shapely.to_wkb(shapely.normalize(shapely.force_2d(geom)))


def _same_point_set(a: BaseGeometry, b: BaseGeometry) -> bool:
    if a.is_empty or b.is_empty:
        return a.is_empty and b.is_empty
    try:
        return bool(shapely.equals(a, b))
    except Exception:  # invalid geometry GEOS refuses to compare topologically
        return _canonical_wkb(a) == _canonical_wkb(b)


def dedupe_geoms(geoms: Iterable[BaseGeometry]) -> List[BaseGeometry]:
    """Return ``geoms`` with duplicates removed, keeping the first occurrence.

    Parameters
    ----------
    geoms:
        An iterable of shapely geometries.  ``None`` entries are treated as a
        single distinct value (the first ``None`` is kept).

    Returns
    -------
    list
        A new list, in the original order, containing one representative per
        distinct point set.  Input geometries are returned as-is (not copied).
    """
    result: List[BaseGeometry] = []
    buckets: dict = {}
    seen_none = False

    for geom in geoms:
        if geom is None:
            if not seen_none:
                seen_none = True
                result.append(geom)
            continue
        if not isinstance(geom, BaseGeometry):
            raise TypeError(
                f"dedupe_geoms expects shapely geometries, got {type(geom).__name__}"
            )

        key = _bucket_key(geom)
        bucket = buckets.setdefault(key, [])
        if any(_same_point_set(geom, prior) for prior in bucket):
            continue
        bucket.append(geom)
        result.append(geom)

    return result
```