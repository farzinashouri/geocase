```python
"""Geodesic length of EPSG:4326 (WGS84 lon/lat) linestrings.

Each segment is measured along the geodesic -- the shortest path on the WGS84
ellipsoid between consecutive vertices -- via pyproj's implementation of
Karney's inverse algorithm. That keeps results accurate anywhere on Earth
(high latitudes, antimeridian crossings, segments of any length, near-antipodal
endpoints) without choosing a projection or a local UTM zone.
"""

from __future__ import annotations

import numpy as np
import shapely
from pyproj import Geod
from shapely.geometry import LineString

__all__ = ["length_m"]

# Pure construction: no I/O, no global state, so importing this module is inert.
_GEOD = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the geodesic length of ``line`` in meters.

    Parameters
    ----------
    line:
        A shapely ``LineString`` (or ``LinearRing``) whose coordinates are
        longitude/latitude in degrees, EPSG:4326. Any Z values are ignored:
        the result is ground length, not slope length.

    Returns
    -------
    float
        Length in meters. Empty geometries and single-vertex lines return 0.0.
    """
    if not isinstance(line, LineString):
        raise TypeError(f"expected a shapely LineString, got {type(line).__name__}")

    coords = shapely.get_coordinates(line)  # (N, 2) array of lon/lat, Z dropped
    if coords.shape[0] < 2:
        return 0.0

    # pyproj wants contiguous buffers; the column slices above are strided.
    lons = np.ascontiguousarray(coords[:, 0])
    lats = np.ascontiguousarray(coords[:, 1])

    return float(_GEOD.line_length(lons, lats))
```