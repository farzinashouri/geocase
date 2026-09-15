from pyproj import Geod
from shapely.geometry import LineString

_geod = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    lons, lats = zip(*line.coords)
    _, _, distances = _geod.inv(lons[:-1], lats[:-1], lons[1:], lats[1:])
    return float(sum(distances))