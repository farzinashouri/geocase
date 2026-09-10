from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid


def fix_geometry(geom):
    """
    Fix an invalid Polygon or MultiPolygon.
    
    Converts an invalid geometry (e.g., self-intersecting) into a valid one
    that covers exactly the region enclosed by the input's boundary rings.
    
    Args:
        geom: A shapely Polygon or MultiPolygon (may be invalid)
    
    Returns:
        A valid shapely Polygon or MultiPolygon covering the same region
    """
    return make_valid(geom)