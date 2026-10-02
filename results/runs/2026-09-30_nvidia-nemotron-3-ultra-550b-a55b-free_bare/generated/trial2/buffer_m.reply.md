```python
"""
Module for buffering geometries in meters while staying in EPSG:4326.

Uses a local Azimuthal Equidistant projection centered on the geometry's centroid
to perform the buffering in a metric coordinate system, then transforms back to
WGS84 (EPSG:4326). This provides accurate results anywhere on Earth for moderate
buffer distances.
"""

from functools import lru_cache
import pyproj
from shapely.geometry import BaseGeometry
from shapely.ops import transform


@lru_cache(maxsize=32)
def _get_transformers(lon: float, lat: float):
    """
    Create forward and inverse transformers for an Azimuthal Equidistant projection
    centered at (lon, lat). Cached for performance.
    """
    # Azimuthal Equidistant projection centered on the given point
    aeqd_crs = pyproj.CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 "
        "+datum=WGS84 +units=m +no_defs"
    )
    wgs84_crs = pyproj.CRS.from_epsg(4326)

    # Always use (x, y) = (lon, lat) order for geographic CRS
    transformer_to_aeqd = pyproj.Transformer.from_crs(
        wgs84_crs, aeqd_crs, always_xy=True
    )
    transformer_to_wgs84 = pyproj.Transformer.from_crs(
        aeqd_crs, wgs84_crs, always_xy=True
    )

    def forward(x, y, z=None):
        return transformer_to_aeqd.transform(x, y)

    def inverse(x, y, z=None):
        return transformer_to_wgs84.transform(x, y)

    return forward, inverse


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """
    Buffer a geometry (in EPSG:4326) by a distance in meters.

    Parameters
    ----------
    geom : shapely.geometry.BaseGeometry
        Input geometry with coordinates in longitude/latitude (EPSG:4326).
    distance_m : float
        Buffer distance in meters. Must be non-negative.

    Returns
    -------
    shapely.geometry.BaseGeometry
        Buffered geometry in EPSG:4326.

    Notes
    -----
    The function projects the geometry to a local Azimuthal Equidistant projection
    centered on the geometry's centroid, performs the buffer operation in that
    metric coordinate system, and projects the result back to EPSG:4326.
    This yields accurate results globally for distances up to a few hundred
    kilometers. For very large distances, consider using a geodesic buffer
    implementation.
    """
    if geom.is_empty:
        return geom

    if distance_m < 0:
        raise ValueError("Buffer distance must be non-negative.")

    # Centroid in (lon, lat) order
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y

    forward, inverse = _get_transformers(lon, lat)

    # Project to metric CRS
    geom_proj = transform(forward, geom)

    # Buffer in meters
    buffered_proj = geom_proj.buffer(distance_m)

    # Project back to EPSG:4326
    buffered_geom = transform(inverse, buffered_proj)

    return buffered_geom
```