"""Deduplicate a list of shapely geometries by point-set equality."""
from __future__ import annotations

from typing import List

from shapely.geometry.base import BaseGeometry


def dedupe_geoms(geoms: List[BaseGeometry]) -> List[BaseGeometry]:
    """Return geoms with duplicates removed, keeping first occurrence order.

    Two geometries are treated as duplicates when they describe the same
    set of points in the plane, regardless of coordinate ordering (e.g. a
    ring traced from a different starting vertex or in the opposite
    winding direction).
    """
    seen = set()
    result: List[BaseGeometry] = []
    for geom in geoms:
        key = geom.normalize().wkb_hex
        if key not in seen:
            seen.add(key)
            result.append(geom)
    return result