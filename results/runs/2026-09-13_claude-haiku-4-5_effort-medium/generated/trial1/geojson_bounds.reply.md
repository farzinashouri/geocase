```python
import json
from shapely.geometry import shape
from shapely.ops import unary_union

def geojson_bounds(path):
    with open(path, 'r') as f:
        geojson = json.load(f)
    
    if 'features' in geojson:
        features = geojson['features']
    elif 'geometry' in geojson:
        features = [geojson]
    else:
        features = [{'geometry': geojson}]
    
    geometries = [shape(f['geometry']) for f in features]
    combined = unary_union(geometries)
    
    return tuple(combined.bounds)
```