"""Module for deduplicating Shapely geometries based on geometric equality."""

import shapely


def dedupe_geoms(geoms):
    """
    Remove duplicate geometries from a list, preserving the first occurrence and order.

    Two geometries are considered duplicates if they describe exactly the same set of
    points in the plane (i.e., they are geometrically equal), even if their coordinate
    sequences differ (e.g., different starting vertex or ring direction).

    Parameters
    ----------
    geoms : list[shapely.Geometry]
        List of Shapely geometry objects.

    Returns
    -------
    list[shapely.Geometry]
        New list containing only the first occurrence of each unique geometry,
        in the original order.
    """
    seen = set()
    result = []
    for geom in geoms:
        # Normalize to a canonical form (e.g., rings start at lowest coordinate,
        # consistent orientation) so that geometrically equal geometries produce
        # identical WKB.
        normalized = shapely.normalize(geom)
        # Use WKB without SRID as a hashable representation.
        wkb = shapely.to_wkb(normalized, include_srid=False)
        if wkb not in seen:
            seen.add(wkb)
            result.append(geom)
    return result