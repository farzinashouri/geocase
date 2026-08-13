```python
import pyproj
from shapely.geometry import base
from shapely.ops import transform

def buffer_m(geom: base.BaseGeometry, distance_m: float) -> base.BaseGeometry:
    """
    Buffer a geometry (in EPSG:4326) by a distance in meters.

    Parameters
    ----------
    geom : shapely.geometry.BaseGeometry
        Input geometry with coordinates in EPSG:4326 (longitude, latitude).
    distance_m : float
        Buffer distance in meters.

    Returns
    -------
    shapely.geometry.BaseGeometry
        Buffered geometry in EPSG:4326.
    """
    if geom.is_empty:
        return geom

    # Centroid in geographic coordinates (lon, lat)
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y

    # Azimuthal equidistant projection centered on the centroid
    # This projection preserves distances from the center point.
    proj_crs = pyproj.CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )
    geographic_crs = pyproj.CRS.from_epsg(4326)

    # Transformers: geographic -> projected and projected -> geographic
    to_projected = pyproj.Transformer.from_crs(geographic_crs, proj_crs, always_xy=True).transform
    to_geographic = pyproj.Transformer.from_crs(proj_crs, geographic_crs, always_xy=True).transform

    # Project geometry to the local metric CRS
    geom_proj = transform(to_projected, geom)

    # Buffer in meters
    buffered_proj = geom_proj.buffer(distance_m)

    # Project back to EPSG:4326
    buffered_geo = transform(to_geographic, buffered_proj)

    return buffered_geo
```