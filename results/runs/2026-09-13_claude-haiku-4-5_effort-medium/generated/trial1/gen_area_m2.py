from shapely.geometry import MultiPolygon
from pyproj import Geod


def area_m2(geom):
    if isinstance(geom, MultiPolygon):
        return sum(area_m2(g) for g in geom.geoms)
    
    geod = Geod(ellps='WGS84')
    
    lons, lats = geom.exterior.xy
    area, _ = geod.polygon_area_perimeter(list(lons), list(lats))
    area = abs(area)
    
    for interior in geom.interiors:
        lons, lats = interior.xy
        hole_area, _ = geod.polygon_area_perimeter(list(lons), list(lats))
        area -= abs(hole_area)
    
    return area