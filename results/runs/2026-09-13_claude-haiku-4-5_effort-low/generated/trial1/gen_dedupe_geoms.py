def dedupe_geoms(geoms):
    """
    Remove duplicate geometries from a list, keeping the first occurrence.

    Two geometries are considered duplicates if they describe the same set of points,
    regardless of coordinate ordering.

    Args:
        geoms: List of shapely geometries

    Returns:
        New list with duplicate geometries removed, preserving order
    """
    result = []
    for geom in geoms:
        if not any(geom.equals(existing) for existing in result):
            result.append(geom)
    return result