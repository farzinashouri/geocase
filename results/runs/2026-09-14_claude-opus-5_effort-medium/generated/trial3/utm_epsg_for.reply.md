```python
"""UTM EPSG codes for WGS 84 locations, using MGRS grid-zone numbering.

The zone number for a point is normally ``floor((lon + 180) / 6) + 1``, but the
Military Grid Reference System defines two published exceptions to that rule:

* Latitude band V (56N-64N): zone 32 is widened westward to 3E, so the strip
  3E-12E belongs to zone 32 instead of being split between zones 31 and 32.
* Latitude band X (72N-84N): zones 32, 34 and 36 do not exist; zones 31, 33,
  35 and 37 are widened to cover 0E-9E, 9E-21E, 21E-33E and 33E-42E.

The returned code is ``32600 + zone`` in the northern hemisphere and
``32700 + zone`` in the southern one.
"""

from __future__ import annotations

import math

__all__ = ["utm_epsg_for"]

# Latitude limits of the UTM/MGRS grid: band C starts at 80S, band X ends at 84N.
_MIN_LAT = -80.0
_MAX_LAT = 84.0

# (eastern limit of the widened zone, zone number) for latitude band X.
_SVALBARD_ZONES = ((9.0, 31), (21.0, 33), (33.0, 35), (42.0, 37))


def _normalize_longitude(lon: float) -> float:
    """Wrap a longitude into [-180, 180)."""
    wrapped = math.fmod(lon + 180.0, 360.0)
    if wrapped < 0.0:
        wrapped += 360.0
    return wrapped - 180.0


def utm_epsg_for(lon, lat) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS covering ``(lon, lat)``.

    Parameters
    ----------
    lon, lat:
        WGS84 longitude and latitude in decimal degrees. Longitudes outside
        [-180, 180) are wrapped.

    Raises
    ------
    ValueError
        If the inputs are not finite, if the latitude is outside [-90, 90], or
        if the point lies in a polar region (outside 80S-84N) that the UTM grid
        does not cover.
    """
    lon = float(lon)
    lat = float(lat)

    if not math.isfinite(lon) or not math.isfinite(lat):
        raise ValueError("lon and lat must be finite numbers")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude out of range: {lat}")
    if lat < _MIN_LAT or lat >= _MAX_LAT:
        raise ValueError(
            f"latitude {lat} lies outside the UTM grid (80S to 84N); "
            "the polar regions use UPS, not UTM"
        )

    lon = _normalize_longitude(lon)

    # Latitude band X: Svalbard exceptions (zones 32, 34, 36 are absent).
    if 72.0 <= lat < 84.0 and 0.0 <= lon < 42.0:
        for eastern_limit, zone in _SVALBARD_ZONES:
            if lon < eastern_limit:
                break
    # Latitude band V: zone 32 is widened west to 3E at Norway's expense.
    elif 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        zone = 32
    else:
        zone = int(math.floor((lon + 180.0) / 6.0)) + 1
        # Guard against floating-point drift at the antimeridian.
        zone = min(max(zone, 1), 60)

    return (32600 if lat >= 0.0 else 32700) + zone
```