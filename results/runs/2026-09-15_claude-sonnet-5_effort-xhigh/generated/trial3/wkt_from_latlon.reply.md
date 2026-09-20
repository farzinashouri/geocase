```python
"""Convert WGS84 latitude/longitude pairs to WKT POINT strings."""

from __future__ import annotations

import math

from shapely.geometry import Point


def wkt_from_latlon(lat: float, lon: float) -> str:
    """Build a WKT POINT string from a WGS84 latitude/longitude pair.

    Args:
        lat: Latitude in decimal degrees, WGS84, range [-90, 90].
        lon: Longitude in decimal degrees, WGS84, range [-180, 180].

    Returns:
        A WKT string such as "POINT (lon lat)". WKT/GIS tools order point
        coordinates as (x, y) = (longitude, latitude) — the reverse of this
        function's (lat, lon) argument order — so the input is swapped
        before being written out.

    Raises:
        ValueError: If lat or lon is not a finite number, or falls outside
            its valid WGS84 range.
    """
    lat = float(lat)
    lon = float(lon)

    if not math.isfinite(lat) or not math.isfinite(lon):
        raise ValueError(f"lat/lon must be finite numbers, got lat={lat}, lon={lon}")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"lat must be in [-90, 90], got {lat}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"lon must be in [-180, 180], got {lon}")

    return Point(lon, lat).wkt
```