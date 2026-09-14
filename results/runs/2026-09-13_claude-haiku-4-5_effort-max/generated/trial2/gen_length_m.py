from shapely.geometry import LineString
from pyproj import Geod

def length_m(line: LineString) -> float:
    geod = Geod(ellps='WGS84')
    total_length = 0.0
    coords = list(line.coords)
    
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        _, _, distance = geod.inv(lon1, lat1, lon2, lat2)
        total_length += distance
    
    return total_length