from shapely.geometry import LineString
from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    coords = list(line.coords)
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        _, _, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
        total += dist
    return total