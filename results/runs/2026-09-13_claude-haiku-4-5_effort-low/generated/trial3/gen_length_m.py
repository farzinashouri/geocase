from shapely.geometry import LineString
from pyproj import Geod


def length_m(line: LineString) -> float:
    """Calculate length of a LineString in meters using geodesic distance.
    
    Args:
        line: A shapely LineString with coordinates in EPSG:4326 (WGS84)
        
    Returns:
        Length in meters as a float
    """
    geod = Geod(ellps='WGS84')
    coords = list(line.coords)
    
    total_distance = 0.0
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        _, _, distance = geod.inv(lon1, lat1, lon2, lat2)
        total_distance += distance
    
    return total_distance