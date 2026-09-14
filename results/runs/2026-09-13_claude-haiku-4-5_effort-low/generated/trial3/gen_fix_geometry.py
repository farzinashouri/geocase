"""Geometry fixing utility for invalid Polygons and MultiPolygons."""


def fix_geometry(geom):
    """
    Fix an invalid Polygon or MultiPolygon.
    
    Args:
        geom: A shapely Polygon or MultiPolygon that may be invalid
              (e.g., self-intersecting).
    
    Returns:
        A valid shapely Polygon or MultiPolygon covering exactly the
        region enclosed by the input's boundary. Already-valid input
        is returned covering the same region.
    """
    return geom.make_valid()