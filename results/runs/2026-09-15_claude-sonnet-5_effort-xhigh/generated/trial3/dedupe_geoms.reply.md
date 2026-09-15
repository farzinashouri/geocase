```python
"""Remove duplicate geometries, keeping the first occurrence of each.

Two geometries are considered duplicates when they describe the same set of
points in the plane, regardless of how their coordinates are sequenced (for
example, a ring recorded from a different starting vertex, or traced in the
opposite direction). Geometric normalization is used to bring every geometry
into a canonical coordinate order before comparing, so such variants collapse
to a single entry.
"""

from __future__ import annotations

from typing import List, Sequence

import shapely
from shapely.geometry.base import BaseGeometry


def dedupe_geoms(geoms: Sequence[BaseGeometry]) -> List[BaseGeometry]:
    """Return `geoms` with point-set duplicates removed, order preserved."""
    seen: set[str] = set()
    result: List[BaseGeometry] = []
    for geom in geoms:
        key = shapely.normalize(geom).wkb_hex
        if key not in seen:
            seen.add(key)
            result.append(geom)
    return result
```