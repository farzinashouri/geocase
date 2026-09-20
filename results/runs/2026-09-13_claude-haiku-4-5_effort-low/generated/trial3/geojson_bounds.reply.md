```python
import json
from shapely.geometry import shape

def geojson_bounds(path):
    with open(path) as f:
        data = json.load(f)
    
    # Determine the list of features based on the GeoJSON type
    if data.get('type') == 'FeatureCollection':
        features = data.get('features', [])
    elif data.get('type') == 'Feature':
        features = [data]
    else:
        # It's a Geometry object directly
        features = [{'geometry': data}]
    
    # Collect bounds from all valid geometries
    all_bounds = []
    for feature in features:
        geometry = feature.get('geometry')
        if geometry is not None:
            geom = shape(geometry)
            if not geom.is_empty:
                all_bounds.append(geom.bounds)
    
    # If no valid geometries, return default bounds
    if not all_bounds:
        return (0.0, 0.0, 0.0, 0.0)
    
    # Compute overall bounds
    min_lon = min(b[0] for b in all_bounds)
    min_lat = min(b[1] for b in all_bounds)
    max_lon = max(b[2] for b in all_bounds)
    max_lat = max(b[3] for b in all_bounds)
    
    return (min_lon, min_lat, max_lon, max_lat)
```