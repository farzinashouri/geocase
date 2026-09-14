```python
from shapely.ops import transform
import pyproj


def area_m2(geom):
    """Calculate area of WGS84 (EPSG:4326) geometry in square meters."""
    # Determine UTM zone from geometry centroid
    minx, miny, maxx, maxy = geom.bounds
    centroid_lon = (minx + maxx) / 2
    centroid_lat = (miny + maxy) / 2
    
    # Calculate UTM zone (1-60)
    utm_zone = int((centroid_lon + 180) / 6) + 1
    
    # Select EPSG code based on hemisphere
    utm_epsg = 32600 + utm_zone if centroid_lat >= 0 else 32700 + utm_zone
    
    # Create transformer from WGS84 to appropriate UTM zone
    transformer = pyproj.Transformer.from_crs(
        "EPSG:4326",
        f"EPSG:{utm_epsg}",
        always_xy=True
    )
    
    # Transform geometry and calculate area
    projected_geom = transform(transformer.transform, geom)
    return float(projected_geom.area)
```