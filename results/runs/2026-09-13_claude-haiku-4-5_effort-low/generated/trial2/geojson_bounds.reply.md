```python
import json
from shapely.geometry import shape

def geojson_bounds(path):
    with open(path) as f:
        geojson = json.load(f)
    
    features = geojson['features']
    bounds_list = [shape(f['geometry']).bounds for f in features]
    
    min_lon = min(b[0] for b in bounds_list)
    min_lat = min(b[1] for b in bounds_list)
    max_lon = max(b[2] for b in bounds_list)
    max_lat = max(b[3] for b in bounds_list)
    
    return (min_lon, min_lat, max_lon, max_lat)
```