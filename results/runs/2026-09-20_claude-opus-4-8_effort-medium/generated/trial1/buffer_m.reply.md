```python
"""Buffer a WGS84 (EPSG:4326) shapely geometry by a distance in meters.

The buffer is computed in a local azimuthal equidistant projection centred on
the geometry, which keeps distances accurate near the geometry anywhere on
Earth, then transformed back to lon/lat. Importing this module has no side
effects.
"""

from __future__ import annotations

from shapely.geometry.base import BaseGeometry
from shapely.ops import transform
from pyproj import CRS, Transformer

_WGS84 = CRS.from_epsg(4326)


def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """Return ``geom`` buffered by ``distance_m`` metres.

    Parameters
    ----------
    geom:
        A shapely geometry whose coordinates are longitude/latitude in
        EPSG:4326 (WGS84).
    distance_m:
        Buffer distance in metres (positive expands the geometry).

    Returns
    -------
    BaseGeometry
        The buffered geometry, again in EPSG:4326.
    """
    if geom.is_empty:
        return geom

    # Centre the local projection on the geometry so the region of interest
    # stays close to the projection origin, where an azimuthal equidistant
    # projection preserves distances from that origin.
    centroid = geom.centroid
    lon0, lat0 = centroid.x, centroid.y

    local_crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )

    fwd = Transformer.from_crs(_WGS84, local_crs, always_xy=True)
    inv = Transformer.from_crs(local_crs, _WGS84, always_xy=True)

    local_geom = transform(fwd.transform, geom)
    buffered = local_geom.buffer(distance_m)
    return transform(inv.transform, buffered)
```