import json
from shapely.geometry import shape

def geojson_bounds(path):
    with open(path) as f:
        geojson = json.load(f)
    
    bounds_list = []
    
    if geojson.get('type') == 'FeatureCollection':
        geometries = [f.get('geometry') for f in geojson.get('features', []) if f.get('geometry')]
    elif geojson.get('type') == 'Feature':
        geom = geojson.get('geometry')
        geometries = [geom] if geom else []
    else:
        geometries = [geojson]
    
    for geom_dict in geometries:
        if geom_dict:
            shape_geom = shape(geom_dict)
            if not shape_geom.is_empty:
                bounds_list.append(shape_geom.bounds)
    
    if not bounds_list:
        raise ValueError("No valid geometries found in GeoJSON")
    
    min_lon = min(b[0] for b in bounds_list)
    min_lat = min(b[1] for b in bounds_list)
    max_lon = max(b[2] for b in bounds_list)
    max_lat = max(b[3] for b in bounds_list)
    
    return (min_lon, min_lat, max_lon, max_lat)