```python
"""
utm_epsg.py

A tiny utility that returns the EPSG code for the UTM zone that covers a given
WGS84 longitude and latitude.

The function is pure and has no side effects on import.
"""

from __future__ import annotations

import math
from typing import Final

__all__: Final[list[str]] = ["utm_epsg_for"]


def utm_epsg_for(lon: float, lat: float) -> int:
    """
    Return the EPSG code of the UTM coordinate reference system that is
    appropriate for the given WGS84 longitude and latitude.

    Parameters
    ----------
    lon : float
        Longitude in degrees, in the range [-180, 180].
    lat : float
        Latitude in degrees, in the range [-90, 90].

    Returns
    -------
    int
        The EPSG code of the UTM zone that covers the point.

    Notes
    -----
    * UTM zones are numbered 1–60, each covering 6° of longitude.
    * For latitudes north of the equator (lat >= 0) the EPSG codes are
      32601–32660.
    * For latitudes south of the equator (lat < 0) the EPSG codes are
      32701–32760.
    * The function handles the special case of longitude 180° by assigning
      it to zone 60, which is the correct behaviour for the UTM grid.
    """
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"Longitude {lon} out of range [-180, 180]")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"Latitude {lat} out of range [-90, 90]")

    # Determine the UTM zone number (1–60)
    if lon == 180.0:
        zone = 60
    else:
        zone = int(math.floor((lon + 180.0) / 6.0)) + 1

    # Determine the EPSG prefix based on hemisphere
    epsg_prefix = 32600 if lat >= 0 else 32700

    return epsg_prefix + zone
```