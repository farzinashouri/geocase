"""Deduplicate shapely geometries by the set of points they cover.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import List, Sequence


def dedupe_geoms(geoms: Sequence) -> List:
    """Return a new list of geometries with duplicates removed.

    The first occurrence of each distinct geometry is kept and the original
    order is preserved. Two geometries are treated as duplicates when they
    describe exactly the same set of points in the plane, regardless of how
    their coordinate sequences are written (e.g. a ring started at a
    different vertex or traced in the opposite direction).
    """
    unique: List = []
    for geom in geoms:
        if not any(_same_point_set(geom, kept) for kept in unique):
            unique.append(geom)
    return unique


def _same_point_set(a, b) -> bool:
    """True when two geometries cover exactly the same points.

    ``shapely``'s ``equals`` performs topological (set-of-points) comparison,
    so it is insensitive to vertex order, ring orientation, and starting
    vertex. A cheap type check short-circuits the common mismatched case, and
    a bounds check avoids the expensive predicate when envelopes differ.
    """
    if a is b:
        return True
    if a is None or b is None:
        return a is b
    if a.is_empty or b.is_empty:
        return a.is_empty and b.is_empty
    if a.geom_type != b.geom_type:
        # Different types can still be spatially equal (e.g. a degenerate
        # collection), so fall through to the exact predicate rather than
        # returning False here.
        pass
    if a.bounds != b.bounds:
        return False
    return a.equals(b)