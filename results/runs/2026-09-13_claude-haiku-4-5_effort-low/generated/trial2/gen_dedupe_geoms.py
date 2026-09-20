def dedupe_geoms(geoms):
    """Remove duplicate geometries from a list, keeping first occurrence and preserving order."""
    result = []
    for geom in geoms:
        if not any(geom.equals(seen) for seen in result):
            result.append(geom)
    return result