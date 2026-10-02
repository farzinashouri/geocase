```python
"""
Module for buffering geometries in EPSG:4326 by a distance in meters.
"""

from shapely.geometry import base
from shapely.ops import transform
import pyproj


def buffer_m(geom: base.BaseGeometry, distance_m: float) -> base.BaseGeometry:
    """
    Buffer a geometry (in EPSG:4326) by a distance in meters.

    The geometry is projected to an azimuthal equidistant projection centered
    on its centroid, buffered in meters, and then projected back to EPSG:4326.

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

    # Centroid in EPSG:4326 (lon, lat)
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y

    # Define azimuthal equidistant projection centered on the centroid
    aeqd_proj = pyproj.CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 "
        "+datum=WGS84 +units=m +no_defs"
    )
    wgs84 = pyproj.CRS.from_epsg(4326)

    # Create transformers
    to_aeqd = pyproj.Transformer.from_crs(wgs84, aeqd_proj, always_xy=True).transform
    to_wgs84 = pyproj.Transformer.from_crs(aeqd_proj, wgs84, always_xy=True).transform

    # Project to azimuthal equidistant, buffer, project back
    geom_proj = transform(to_aeqd, geom)
    buffered_proj = geom_proj.buffer(distance_m)
    buffered_wgs84 = transform(to_wgs84, buffered_proj)

    return buffered_wgs84
```