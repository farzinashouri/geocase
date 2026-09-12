```python
from shapely.geometry import mapping
from shapely import transform
from pyproj import CRS, Transformer


def to_rfc7946(geom, epsg):
    """Convert a shapely geometry to RFC 7946 GeoJSON format."""
    if epsg != 4326:
        source_crs = CRS.from_epsg(epsg)
        target_crs = CRS.from_epsg(4326)
        transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
        geom = transform(geom, transformer.transform)
    
    geojson_dict = mapping(geom)
    return {
        'type': geojson_dict['type'],
        'coordinates': geojson_dict['coordinates']
    }
```