import json
from shapely.geometry import shape


def geojson_bounds(path):
    with open(path) as f:
        geojson = json.load(f)
    
    geometries = []
    
    if geojson.get('type') == 'FeatureCollection':
        for feature in geojson['features']:
            geometries.append(shape(feature['geometry']))
    elif geojson.get('type') == 'Feature':
        geometries.append(shape(geojson['geometry']))
    else:
        geometries.append(shape(geojson))
    
    min_lon = float('inf')
    min_lat = float('inf')
    max_lon = float('-inf')
    max_lat = float('-inf')
    
    for geom in geometries:
        if not geom.is_empty:
            minx, miny, maxx, maxy = geom.bounds
            min_lon = min(min_lon, minx)
            min_lat = min(min_lat, miny)
            max_lon = max(max_lon, maxx)
            max_lat = max(max_lat, maxy)
    
    return (min_lon, min_lat, max_lon, max_lat)