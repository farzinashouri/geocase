import json
from shapely.geometry import shape

def geojson_bounds(path):
    with open(path, 'r') as f:
        geojson = json.load(f)
    
    if geojson.get('type') == 'FeatureCollection':
        features = geojson.get('features', [])
    elif geojson.get('type') == 'Feature':
        features = [geojson]
    else:
        features = [{'type': 'Feature', 'geometry': geojson}]
    
    bounds_list = []
    for feature in features:
        if feature.get('type') == 'Feature':
            geom_dict = feature.get('geometry')
        else:
            geom_dict = feature
        
        if geom_dict:
            try:
                geom = shape(geom_dict)
                if not geom.is_empty:
                    bounds_list.append(geom.bounds)
            except Exception:
                pass
    
    if not bounds_list:
        return (0.0, 0.0, 0.0, 0.0)
    
    min_lon = min(b[0] for b in bounds_list)
    min_lat = min(b[1] for b in bounds_list)
    max_lon = max(b[2] for b in bounds_list)
    max_lat = max(b[3] for b in bounds_list)
    
    return (float(min_lon), float(min_lat), float(max_lon), float(max_lat))