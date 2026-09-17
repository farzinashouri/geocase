"""WKT point construction from WGS84 latitude/longitude.

WKT (and GIS tools generally) order coordinates as X Y, i.e. longitude
before latitude. User-facing APIs conventionally supply (lat, lon), so this
module swaps the axis order when building the string.
"""

import math


def wkt_from_latlon(lat, lon):
    """Return a WKT ``POINT`` for a WGS84 location given as (lat, lon).

    The returned string is ``POINT (lon lat)`` -- X then Y -- which is the
    axis order expected by shapely, PostGIS, GDAL/OGR, QGIS and other
    standard GIS tools.

    Raises ``TypeError`` for non-numeric input and ``ValueError`` for NaN,
    infinity, or coordinates outside the WGS84 range.
    """
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            f"lat and lon must be numeric, got {lat!r}, {lon!r}"
        ) from exc

    if isinstance(lat, bool) or isinstance(lon, bool):
        raise TypeError("lat and lon must be numeric, not bool")

    if not (math.isfinite(lat_f) and math.isfinite(lon_f)):
        raise ValueError(f"lat and lon must be finite, got {lat_f}, {lon_f}")

    if not -90.0 <= lat_f <= 90.0:
        raise ValueError(f"latitude {lat_f} out of range [-90, 90]")
    if not -180.0 <= lon_f <= 180.0:
        raise ValueError(f"longitude {lon_f} out of range [-180, 180]")

    # repr() gives the shortest round-trippable decimal form; format 'r'
    # is not available, so use repr via !r on floats.
    return f"POINT ({lon_f!r} {lat_f!r})"