```python
from shapely.ops import transform
from pyproj import Transformer, CRS


def buffer_m(geom, distance_m):
    """Buffer a WGS84 geometry by a distance in meters."""
    
    # Get the centroid to determine the appropriate projection
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y
    
    # Create a local azimuthal equidistant projection centered on the geometry
    proj_str = f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 +ellps=WGS84"
    
    from_crs = CRS.from_epsg(4326)
    to_crs = CRS.from_proj4(proj_str)
    
    to_proj = Transformer.from_crs(from_crs, to_crs, always_xy=True)
    from_proj = Transformer.from_crs(to_crs, from_crs, always_xy=True)
    
    geom_proj = transform(to_proj.transform, geom)
    geom_buffered = geom_proj.buffer(distance_m)
    geom_result = transform(from_proj.transform, geom_buffered)
    
    return geom_result
```