```python
# buffer_m.py
"""
A small self‑contained module that provides a function to buffer a Shapely geometry
by a specified distance in metres, using a locally accurate projection.
"""

from __future__ import annotations

import pyproj
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """
    Buffer a Shapely geometry by a specified distance in metres.

    Parameters
    ----------
    geom : shapely.geometry.base.BaseGeometry
        Geometry with coordinates in EPSG:4326 (longitude/latitude).
    distance_m : float
        Buffer distance in metres. Can be negative to shrink the geometry.

    Returns
    -------
    shapely.geometry.base.BaseGeometry
        The buffered geometry, still in EPSG:4326.
    """
    if geom.is_empty:
        return geom

    # Determine a suitable local projection (Azimuthal Equidistant)
    centroid = geom.centroid
    lon0, lat0 = centroid.x, centroid.y

    # Create transformers: WGS84 <-> local aeqd projection
    proj_wgs84 = "EPSG:4326"
    proj_aeqd = (
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +datum=WGS84 +units=m +no_defs"
    )
    to_aeqd = pyproj.Transformer.from_crs(proj_wgs84, proj_aeqd, always_xy=True)
    to_wgs84 = pyproj.Transformer.from_crs(proj_aeqd, proj_wgs84, always_xy=True)

    # Project geometry to metres, buffer, then project back
    geom_proj = transform(to_aeqd.transform, geom)
    buffered_proj = geom_proj.buffer(distance_m)
    buffered_wgs84 = transform(to_wgs84.transform, buffered_proj)

    return buffered_wgs84
```