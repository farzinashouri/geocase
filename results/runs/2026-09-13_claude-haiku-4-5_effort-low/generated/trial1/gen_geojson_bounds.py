import json
from shapely.geometry import shape


def geojson_bounds(path):
    """Returns the bounding box (min_lon, min_lat, max_lon, max_lat) of a GeoJSON file."""
    with open(path, 'r') as f:
        geojson = json.load(f)
    
    min_lon = float('inf')
    min_lat = float('inf')
    max_lon = float('-inf')
    max_lat = float('-inf')
    
    # Get features list
    features = geojson.get('features', [])
    if not features and 'geometry' in geojson:
        features = [geojson]
    
    for feature in features:
        geometry = feature.get('geometry')
        if geometry:
            geom = shape(geometry)
            bounds = geom.bounds
            min_lon = min(min_lon, bounds[0])
            min_lat = min(min_lat, bounds[1])
            max_lon = max(max_lon, bounds[2])
            max_lat = max(max_lat, bounds[3])
    
    return (min_lon, min_lat, max_lon, max_lat)