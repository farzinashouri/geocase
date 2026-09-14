```python
from shapely.ops import transform
import pyproj


def buffer_m(geom, distance_m):
    """
    Buffer a WGS84 geometry by a distance in meters.
    
    Args:
        geom: A shapely geometry with coordinates in EPSG:4326 (WGS84)
        distance_m: Buffer distance in meters
    
    Returns:
        A buffered geometry with coordinates in EPSG:4326
    """
    center = geom.centroid
    
    src_crs = pyproj.CRS("EPSG:4326")
    dst_crs = pyproj.CRS(
        f"+proj=aeqd +lon_0={center.x} +lat_0={center.y} +datum=WGS84 +units=m"
    )
    
    forward = pyproj.Transformer.from_crs(src_crs, dst_crs, always_xy=True)
    backward = pyproj.Transformer.from_crs(dst_crs, src_crs, always_xy=True)
    
    geom_proj = transform(forward.transform, geom)
    geom_buff = geom_proj.buffer(distance_m)
    return transform(backward.transform, geom_buff)
```