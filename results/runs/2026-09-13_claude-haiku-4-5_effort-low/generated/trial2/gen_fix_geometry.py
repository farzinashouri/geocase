from shapely import make_valid

def fix_geometry(geom):
    """Fix invalid geometries while preserving the enclosed region."""
    if geom is None or geom.is_empty:
        return geom
    
    return make_valid(geom)