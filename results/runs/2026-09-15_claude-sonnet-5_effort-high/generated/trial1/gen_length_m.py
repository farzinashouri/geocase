from shapely.geometry import LineString
from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    _, _, distances = _GEOD.inv(
        lons[:-1], lats[:-1], lons[1:], lats[1:]
    )
    return float(sum(distances))