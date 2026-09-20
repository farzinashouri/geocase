from pyproj import Geod
from shapely.geometry import LineString


def length_m(line: LineString) -> float:
    lons, lats = zip(*line.coords)
    geod = Geod(ellps="WGS84")
    return float(geod.line_length(lons, lats))