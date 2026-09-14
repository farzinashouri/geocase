from shapely.geometry import Polygon, MultiPolygon, GeometryCollection


def fix_geometry(geom):
    """
    Fix an invalid Polygon or MultiPolygon, returning a valid geometry covering the same region.
    """
    fixed = geom.make_valid()
    
    if isinstance(fixed, (Polygon, MultiPolygon)):
        return fixed
    
    if isinstance(fixed, GeometryCollection):
        polygons = []
        for part in fixed.geoms:
            if isinstance(part, Polygon):
                polygons.append(part)
            elif isinstance(part, MultiPolygon):
                polygons.extend(part.geoms)
        
        if not polygons:
            return Polygon()
        if len(polygons) == 1:
            return polygons[0]
        return MultiPolygon(polygons)
    
    return Polygon()