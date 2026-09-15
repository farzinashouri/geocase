from pyproj import Geod
from shapely.geometry.base import BaseGeometry


def area_m2(geom: BaseGeometry) -> float:
    geod = Geod(ellps="WGS84")
    area, _perimeter = geod.geometry_area_perimeter(geom)
    return abs(area)