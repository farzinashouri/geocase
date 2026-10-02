import shapely

def dedupe_geoms(geoms):
    """
    Remove duplicate geometries from a list, preserving order.

    Two geometries are considered duplicates if they are geometrically equal
    (i.e., they describe the same set of points in the plane), even if their
    coordinate sequences differ (e.g., different starting vertex or winding order).

    Parameters
    ----------
    geoms : list of shapely.Geometry
        Input geometries.

    Returns
    -------
    list of shapely.Geometry
        List with duplicates removed, keeping the first occurrence of each.
    """
    seen = set()
    result = []
    for geom in geoms:
        # Normalize to a canonical form (ring order, vertex order, etc.)
        norm = shapely.normalize(geom)
        # Use WKB without SRID as a hashable key for geometric equality
        key = shapely.to_wkb(norm, include_srid=False)
        if key not in seen:
            seen.add(key)
            result.append(geom)
    return result