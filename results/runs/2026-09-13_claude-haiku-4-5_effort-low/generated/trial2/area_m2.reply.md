```python
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import transform
from pyproj import Transformer
import math

def area_m2(geom):
    """
    Calculate the area of a polygon or multipolygon in square meters.
    
    Args:
        geom: A shapely Polygon or MultiPolygon with coordinates in EPSG:4326 (WGS84)
    
    Returns:
        Area in square meters as a float
    """
    # Get the centroid to determine the appropriate UTM zone
    centroid = geom.centroid
    lon = centroid.x
    lat = centroid.y
    
    # Calculate UTM zone (UTM zones are 6 degrees wide)
    utm_zone = math.floor((lon + 180) / 6) + 1
    
    # Determine EPSG code based on hemisphere
    # Northern Hemisphere: 32601-32660, Southern: 32701-32760
    epsg_code = 32600 + utm_zone if lat >= 0 else 32700 + utm_zone
    
    # Create transformer from WGS84 to UTM
    transformer = Transformer.from_epsg(4326, epsg_code)
    
    # Define transformation function for shapely
    def transform_coords(x, y, z=None):
        xs, ys = transformer.transform(x, y)
        return xs, ys
    
    # Transform geometry to projected coordinate system
    projected_geom = transform(transform_coords, geom)
    
    # Return area in square meters
    return projected_geom.area
```