```python
"""UTM EPSG lookup for WGS 84, following MGRS grid-zone assignment.

``utm_epsg_for(lon, lat)`` returns 326xx (northern hemisphere) or 327xx
(southern), where xx is the MGRS zone number for the point -- including the
published grid exceptions over south-west Norway and Svalbard.
"""

from __future__ import annotations

__all__ = ["utm_epsg_for"]


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180)."""
    lon = float(lon)
    if lon != lon:  # NaN
        raise ValueError("longitude must be a finite number")
    return (lon + 180.0) % 360.0 - 180.0


def _zone_number(lon: float, lat: float) -> int:
    """MGRS zone number for a normalized longitude and a valid latitude."""
    zone = int((lon + 180.0) // 6.0) + 1

    # Exception 1: zone 32 is widened westward over southern Norway,
    # at the expense of zone 31, in latitude band V (56 <= lat < 64).
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        return 32

    # Exception 2: Svalbard, latitude band X (72 <= lat < 84). Zones 32, 34
    # and 36 are not used; 31, 33, 35 and 37 are widened to cover the gaps.
    if 72.0 <= lat < 84.0 and lon >= 0.0:
        if lon < 9.0:
            return 31
        if lon < 21.0:
            return 33
        if lon < 33.0:
            return 35
        if lon < 42.0:
            return 37

    return zone


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS covering ``(lon, lat)``.

    Parameters
    ----------
    lon, lat:
        WGS84 longitude and latitude in decimal degrees. Longitudes outside
        [-180, 180) are wrapped; latitude must lie in [-90, 90].

    Returns
    -------
    int
        326xx in the northern hemisphere, 327xx in the southern, where xx is
        the MGRS zone number.
    """
    lat = float(lat)
    if lat != lat or not -90.0 <= lat <= 90.0:
        raise ValueError("latitude must be within [-90, 90]")

    lon = _normalize_lon(lon)
    zone = _zone_number(lon, lat)
    return (32600 if lat >= 0.0 else 32700) + zone
```