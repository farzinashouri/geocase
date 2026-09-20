from shapely.geometry import LineString
from pyproj import Geod


def length_m(line: LineString) -> float:
    """Calculate the length of a LineString in meters.
    
    Args:
        line: A shapely LineString with coordinates in EPSG:4326 (WGS84)
    
    Returns:
        The length of the line in meters as a float
    """
    if len(line.coords) < 2:
        return 0.0
    
    geod = Geod(ellps='WGS84')
    total_distance = 0.0
    
    coords = list(line.coords)
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        _, _, distance = geod.inv(lon1, lat1, lon2, lat2)
        total_distance += distance
    
    return total_distance