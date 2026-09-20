from pyproj import Geod


def area_m2(geom):
    geod = Geod(ellps="WGS84")
    area, _ = geod.geometry_area_perimeter(geom)
    return float(abs(area))