```python
from shapely.geometry import mapping
from shapely.ops import transform
from pyproj import Transformer


def to_rfc7946(geom, epsg):
    if epsg != 4326:
        transformer = Transformer.from_crs(epsg, 4326, always_xy=True)
        geom = transform(transformer.transform, geom)
    
    geojson = mapping(geom)
    return {'type': geojson['type'], 'coordinates': geojson['coordinates']}
```