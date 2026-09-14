from shapely.geometry import LineString
from pyproj import Geod


def length_m(line: LineString) -> float:
    """Calculate the length of a LineString in meters using geodesic distances."""
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0
    
    geod = Geod(ellps='WGS84')
    total = 0.0
    
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        _, _, distance = geod.inv(lon1, lat1, lon2, lat2)
        total += distance
    
    return total