from shapely import make_valid

def fix_geometry(geom):
    """
    Fix an invalid Polygon or MultiPolygon by making it valid
    while preserving the region enclosed by its boundary.
    
    Args:
        geom: A shapely Polygon or MultiPolygon (may be invalid)
    
    Returns:
        A valid shapely Polygon or MultiPolygon
    """
    return make_valid(geom)