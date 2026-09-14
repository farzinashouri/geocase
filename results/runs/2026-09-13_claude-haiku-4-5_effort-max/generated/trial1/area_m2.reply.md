```python
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import transform
from pyproj import CRS, Transformer

def area_m2(geom):
    """
    Calculate the area of a polygon in square meters.
    
    Args:
        geom: A shapely Polygon or MultiPolygon with coordinates in EPSG:4326 (WGS84)
    
    Returns:
        The area in square meters as a float
    """
    # Get the centroid to determine the UTM zone
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y
    
    # Calculate UTM zone (1-60)
    utm_zone = int((lon + 180) / 6) + 1
    
    # Create EPSG code for appropriate UTM zone
    if lat >= 0:
        epsg_code = 32600 + utm_zone
    else:
        epsg_code = 32700 + utm_zone
    
    # Create transformer from WGS84 to UTM
    transformer = Transformer.from_crs(CRS.from_epsg(4326), CRS.from_epsg(epsg_code), always_xy=True)
    
    # Transform the geometry and calculate area
    transformed_geom = transform(transformer.transform, geom)
    
    return float(transformed_geom.area)
```