from shapely.geometry import LineString
from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    lons, lats = zip(*line.coords)
    return float(_GEOD.line_length(lons, lats))