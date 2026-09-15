"""Deduplicate shapely geometries by the point set they describe.

Two geometries count as duplicates when they are topologically equal: they
cover exactly the same set of points in the plane, however their coordinate
sequences happen to be written.  A ring started at a different vertex or wound
the other way round, parts of a multi-geometry listed in another order, or
redundant collinear vertices all describe the same point set and collapse to a
single entry.  Z values are ignored, matching the planar semantics of the task.
"""

from __future__ import annotations

import shapely
from shapely.errors import GEOSException
from shapely.geometry.base import BaseGeometry

__all__ = ["dedupe_geoms"]


def _bucket_key(geom):
    """A key that topologically equal geometries are guaranteed to share.

    Both components are properties of the point set itself rather than of its
    writing: equal point sets have equal topological dimension and, since the
    extremes of a point set are attained at vertices, bit-identical bounds.
    So geometries landing in different buckets cannot be duplicates and never
    have to be compared.
    """
    return int(shapely.get_dimensions(geom)), geom.bounds


def _canonical_wkb(geom):
    """WKB of the geometry in GEOS' canonical form, flattened to 2D.

    Equal bytes imply equal point sets, so this is a sound fast path.  The
    converse does not hold -- normalization fixes ring start, orientation and
    part order but will not, say, drop a redundant collinear vertex -- so a
    miss falls through to the full topological test.
    """
    return shapely.to_wkb(shapely.normalize(shapely.force_2d(geom)))


def _same_point_set(a, b):
    try:
        return bool(shapely.equals(a, b))
    except GEOSException:
        # Invalid geometry (a self-intersecting polygon, say) can make the
        # topological predicate fail outright.  The canonical-form check has
        # already ruled out an identical writing, so keep both rather than
        # guess.
        return False


def dedupe_geoms(geoms):
    """Return a new list of ``geoms`` with duplicates removed.

    The first occurrence of each distinct geometry is kept and the original
    relative order is preserved.  All empty geometries describe the empty point
    set and therefore collapse to a single entry, whatever their type.

    Raises TypeError if any element is not a shapely geometry.
    """
    unique = []
    buckets = {}
    seen_wkb = set()
    kept_empty = False

    for geom in geoms:
        if not isinstance(geom, BaseGeometry):
            raise TypeError(
                f"expected a shapely geometry, got {type(geom).__name__}"
            )

        if geom.is_empty:
            if kept_empty:
                continue
            kept_empty = True
            unique.append(geom)
            continue

        wkb = _canonical_wkb(geom)
        if wkb in seen_wkb:
            continue

        bucket = buckets.setdefault(_bucket_key(geom), [])
        if any(_same_point_set(geom, kept) for kept in bucket):
            continue

        seen_wkb.add(wkb)
        bucket.append(geom)
        unique.append(geom)

    return unique