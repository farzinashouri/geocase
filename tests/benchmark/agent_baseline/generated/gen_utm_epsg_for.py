"""Determine the appropriate UTM EPSG code for a WGS84 longitude/latitude.

Pure standard-library implementation. Importing this module has no side
effects.
"""

import math

__all__ = ["utm_epsg_for"]


def utm_epsg_for(lon, lat):
    """Return the EPSG code (int) of the WGS84 UTM zone for a location.

    Parameters
    ----------
    lon : float
        WGS84 longitude in decimal degrees, in [-180, 180].
    lat : float
        WGS84 latitude in decimal degrees, in [-90, 90].

    Returns
    -------
    int
        EPSG code: 326xx for the northern hemisphere, 327xx for the
        southern hemisphere, where xx is the UTM zone number (01-60).
        The standard grid exceptions for southwest Norway (zone 32) and
        Svalbard (zones 31/33/35/37) are applied.

    Raises
    ------
    TypeError
        If lon or lat is not a real number.
    ValueError
        If lon or lat is NaN or outside the valid range.
    """
    for name, value in (("lon", lon), ("lat", lat)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("%s must be a real number, got %r" % (name, value))
        if math.isnan(value):
            raise ValueError("%s must not be NaN" % name)

    lon = float(lon)
    lat = float(lat)
    if not -180.0 <= lon <= 180.0:
        raise ValueError("lon must be in [-180, 180], got %r" % lon)
    if not -90.0 <= lat <= 90.0:
        raise ValueError("lat must be in [-90, 90], got %r" % lat)

    # Base zone; the modulo maps lon == 180.0 into zone 1 (its zone wraps
    # around the antimeridian).
    zone = int((lon + 180.0) // 6.0) % 60 + 1

    # Exception: southwest Norway extends zone 32 westward.
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        zone = 32
    # Exceptions: Svalbard uses zones 31, 33, 35, 37.
    elif 72.0 <= lat <= 84.0 and 0.0 <= lon < 42.0:
        if lon < 9.0:
            zone = 31
        elif lon < 21.0:
            zone = 33
        elif lon < 33.0:
            zone = 35
        else:
            zone = 37

    return (32600 if lat >= 0.0 else 32700) + zone
