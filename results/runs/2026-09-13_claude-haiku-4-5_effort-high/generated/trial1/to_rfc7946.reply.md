```python
from shapely.geometry import mapping
from pyproj import Transformer


def to_rfc7946(geom, epsg):
    """
    Convert a shapely geometry to an RFC 7946 compliant GeoJSON geometry object.
    
    Args:
        geom: A shapely geometry object
        epsg: Integer EPSG code of the CRS the geometry is in
    
    Returns:
        dict: A GeoJSON geometry object with 'type' and 'coordinates' members
    """
    # Reproject to WGS84 (EPSG:4326) if needed
    if epsg != 4326:
        transformer = Transformer.from_crs(epsg, 4326, always_xy=True)
        geom = geom.transform(transformer.transform)
    
    # Convert shapely geometry to GeoJSON dict
    geojson = mapping(geom)
    
    # Return only type and coordinates (RFC 7946 geometry object)
    return {
        'type': geojson['type'],
        'coordinates': geojson['coordinates']
    }
```