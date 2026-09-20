"""Deduplicate shapely geometries by geometric identity.

Two geometries are treated as duplicates when they cover exactly the same
set of points in the plane, regardless of how their coordinate sequences are
written -- a ring may start at a different vertex, run in the opposite
direction, or carry extra collinear vertices.
"""

from shapely import geometry  # noqa: F401  (ensures shapely.geometry is importable)


def _canonical_key(geom):
    """A hashable key that is identical for trivially-reordered twins.

    ``normalize`` sorts rings/parts and fixes winding, so rotated or reversed
    versions of the same ring collapse to the same WKB. This is only a fast
    path: keys that differ still get an exact ``equals`` check.
    """
    return geom.normalize().wkb


def _bucket_key(geom):
    """Coarse key grouping geometries that could possibly be equal.

    Equal point sets must share an envelope and emptiness, so comparisons
    never need to cross bucket boundaries.
    """
    if geom.is_empty:
        return ("empty",)
    return geom.bounds


def dedupe_geoms(geoms):
    """Return a list of ``geoms`` with geometric duplicates removed.

    The first occurrence of each distinct geometry is kept and the original
    ordering of those survivors is preserved. The input list and the
    geometries themselves are not modified.

    Parameters
    ----------
    geoms : iterable of shapely geometries

    Returns
    -------
    list
        The retained geometry objects, in input order.
    """
    kept = []
    seen_keys = set()
    buckets = {}

    for geom in geoms:
        if geom is None:
            continue

        key = _canonical_key(geom)
        if key in seen_keys:
            continue

        bucket = buckets.setdefault(_bucket_key(geom), [])
        # Same point set, different vertex counts (e.g. a redundant collinear
        # vertex) survives the WKB check, so fall back to a true set-equality
        # test against the candidates sharing this envelope.
        if any(geom.equals(other) for other in bucket):
            continue

        seen_keys.add(key)
        bucket.append(geom)
        kept.append(geom)

    return kept