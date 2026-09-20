```python
import json
from shapely.geometry import shape, GeometryCollection


def geojson_bounds(path):
    with open(path) as f:
        geojson = json.load(f)
    
    geometries = []
    
    if geojson.get('type') == 'FeatureCollection':
        for feature in geojson.get('features', []):
            if feature.get('geometry'):
                geometries.append(shape(feature['geometry']))
    elif geojson.get('type') == 'Feature':
        if geojson.get('geometry'):
            geometries.append(shape(geojson['geometry']))
    else:
        geometries.append(shape(geojson))
    
    geometries = [g for g in geometries if not g.is_empty]
    
    if not geometries:
        return (0.0, 0.0, 0.0, 0.0)
    
    collection = GeometryCollection(geometries)
    minx, miny, maxx, maxy = collection.bounds
    
    return (minx, miny, maxx, maxy)
```