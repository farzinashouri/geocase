```python
"""
Module for buffering geometries in meters while working in EPSG:4326.
"""

import pyproj
from shapely.geometry import BaseGeometry
from shapely.ops import transform


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """
    Buffer a geometry (in EPSG:4326) by a distance in meters.

    The geometry is projected to a local azimuthal equidistant projection
    centered on its centroid, buffered, and then projected back to EPSG:4326.

    Parameters
    ----------
    geom : BaseGeometry
        Input geometry with coordinates in EPSG:4326 (longitude, latitude).
    distance_m : float
        Buffer distance in meters.

    Returns
    -------
    BaseGeometry
        Buffered geometry in EPSG:4326.
    """
    if geom.is_empty:
        return geom

    # Centroid of the geometry (in EPSG:4326)
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y

    # Local azimuthal equidistant projection centered on the centroid
    proj_crs = pyproj.CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 "
        "+datum=WGS84 +units=m +no_defs"
    )
    wgs84 = pyproj.CRS.from_epsg(4326)

    # Transformers for forward and inverse projections
    to_proj = pyproj.Transformer.from_crs(wgs84, proj_crs, always_xy=True).transform
    to_wgs = pyproj.Transformer.from_crs(proj_crs, wgs84, always_xy=True).transform

    # Project to metric CRS, buffer, project back
    geom_proj = transform(to_proj, geom)
    geom_buffered_proj = geom_proj.buffer(distance_m)
    geom_buffered = transform(to_wgs, geom_buffered_proj)

    return geom_buffered
```