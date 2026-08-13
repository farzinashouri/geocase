```python
from __future__ import annotations

import pyproj
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """
    Return a new geometry that is the input geometry buffered by `distance_m` meters.
    The input geometry must be in EPSG:4326 (longitude/latitude). The result will
    also be in EPSG:4326. The buffering is performed in a local Azimuthal
    Equidistant projection centered on the geometry's centroid to preserve
    distances accurately anywhere on Earth.

    Parameters
    ----------
    geom : shapely.geometry.base.BaseGeometry
        Geometry in EPSG:4326.
    distance_m : float
        Buffer distance in meters. Can be negative to shrink the geometry.

    Returns
    -------
    shapely.geometry.base.BaseGeometry
        Buffered geometry in EPSG:4326.
    """
    if geom.is_empty:
        return geom

    # Compute centroid to center the local projection
    centroid = geom.centroid
    lat = centroid.y
    lon = centroid.x

    # Define an Azimuthal Equidistant projection centered at the centroid
    aeqd_crs = pyproj.CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +units=m +no_defs"
    )

    # Transformers for forward and inverse projection
    to_aeqd = pyproj.Transformer.from_crs(4326, aeqd_crs, always_xy=True)
    to_wgs84 = pyproj.Transformer.from_crs(aeqd_crs, 4326, always_xy=True)

    # Project geometry to the local projection, buffer, then reproject back
    projected = transform(to_aeqd.transform, geom)
    buffered = projected.buffer(distance_m)
    result = transform(to_wgs84.transform, buffered)

    return result
```